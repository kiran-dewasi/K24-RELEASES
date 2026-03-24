import socketio
import logging
import asyncio
import uuid
from typing import Dict, Any, Optional

logger = logging.getLogger("socket_manager")

class K24SocketManager:
    """
    Manages realtime WebSocket connections for Remote Tally Agents.
    Maps Tenant IDs to Socket IDs using python-socketio.
    """
    def __init__(self):
        # Create Async Server
        self.sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
        # Create ASGI App
        self.app = socketio.ASGIApp(self.sio, socketio_path="")
        
        # Track active connections: tenant_id -> sid (and vice versa if needed)
        self.active_tenants: Dict[str, str] = {}
        
        # Pending requests: req_id -> Future
        self.pending_requests: Dict[str, asyncio.Future] = {}
        
        # Register event handlers
        self.sio.on('connect', self.connect)
        self.sio.on('disconnect', self.disconnect)

        self.sio.on('tally_response', self.handle_tally_response)
        self.sio.on('sync_data', self.sync_data)

    async def sync_data(self, sid, data):
        """
        Handle incoming Sync Data from Client Agent.
        """
        from database import SessionLocal, Voucher, Ledger
        from tally_connector import TallyConnector
        from datetime import datetime
        
        # 1. Identify Tenant
        tenant_id = None
        for tid, s in self.active_tenants.items():
            if s == sid:
                tenant_id = tid
                break
        
        if not tenant_id:
            logger.warning(f"Received sync data from unknown SID: {sid}")
            return
            
        xml_data = data.get('xml')
        if not xml_data:
            return

        logger.info(f"🔄 Processing Sync Data for Tenant: {tenant_id}")
        
        # 2. Parse XML
        # Using TallyConnector's static parser
        try:
            df = TallyConnector._parse_voucher_xml(xml_data)
            logger.info(f"Parsed {len(df)} vouchers from XML.")
            
            if df.empty:
                return

            # 3. Save to Database (Simplified)
            db = SessionLocal()
            count = 0
            
            try:
                for _, row in df.iterrows():
                    # Check duplication by guid or voucher_number + type
                    # For MVP, just upsert by voucher_number
                    v_no = row.get('voucher_number')
                    v_type = row.get('voucher_type')
                    if not v_no: continue
                    
                    existing = db.query(Voucher).filter_by(
                        tenant_id=tenant_id, 
                        voucher_number=v_no
                    ).first()
                    
                    # Parse Date safely
                    raw_date = row.get('date')
                    date_obj = None
                    if raw_date:
                        try:
                            if isinstance(raw_date, str):
                                # Clean string
                                raw_date = raw_date.strip()
                                if len(raw_date) == 8 and raw_date.isdigit():
                                    date_obj = datetime.strptime(raw_date, "%Y%m%d")
                                else:
                                    # Fallback to ISO-like YYYY-MM-DD
                                    # Handle "2026-03-30 00:00:00" if pandas left it
                                    if " " in raw_date:
                                        raw_date = raw_date.split(" ")[0]
                                    date_obj = datetime.strptime(raw_date, "%Y-%m-%d")
                            elif hasattr(raw_date, 'to_pydatetime'):
                                # Pandas Timestamp
                                date_obj = raw_date.to_pydatetime()
                            else:
                                date_obj = raw_date # Assume already datetime
                        except Exception as e:
                            logger.warning(f"Date parse error '{raw_date}': {e}")
                            date_obj = datetime.now()
                    else:
                        date_obj = datetime.now()

                    if not existing:
                        new_voucher = Voucher(
                            tenant_id=tenant_id,
                            voucher_number=v_no,
                            voucher_type=v_type,
                            date=date_obj,
                            party_name=row.get('party_name'),
                            amount=row.get('amount') or 0.0,
                            narration=row.get('narration'),
                            guid=f"{tenant_id}-{v_no}" # Mock GUID
                        )
                        db.add(new_voucher)
                        count += 1
                
                db.commit()
                logger.info(f"✅ Saved {count} new vouchers for {tenant_id}")
                
            except Exception as e:
                db.rollback()
                logger.error(f"Database Save Error: {e}")
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Sync Parsing Error: {e}")

    async def connect(self, sid, environ, auth):
        """
        Handle new connection.
        Phase 2 Security: Verifies SIGNED JWT token instead of raw tenant_id.
        """
        logger.info(f"Socket connection attempt: {sid} | Auth present: {bool(auth)}")
        
        if not auth or 'token' not in auth:
            logger.warning(f"Connection rejected: No auth token. SID: {sid}")
            return False  # Reject connection
        
        token = auth.get('token')
        tenant_id = None
        
        # Phase 2: Try to verify as signed JWT first
        try:
            from auth import decode_socket_token
            
            payload = decode_socket_token(token)
            if payload:
                # Signed JWT verified successfully!
                tenant_id = payload.get('tenant_id')
                user_id = payload.get('sub')
                license_key = payload.get('license_key')
                logger.info(f"[SECURE] JWT verified! Tenant: {tenant_id}, User: {user_id}")
            else:
                # Fall back to raw tenant_id for backward compatibility
                # TODO: Remove this fallback after all clients are updated
                logger.warning(f"[COMPAT] Using raw token as tenant_id (upgrade client!)")
                tenant_id = token
                
        except Exception as e:
            logger.warning(f"JWT decode failed, using raw token: {e}")
            tenant_id = token
        
        if not tenant_id:
            logger.warning(f"Connection rejected: No tenant_id. SID: {sid}")
            return False
        
        # Store mapping
        self.active_tenants[tenant_id] = sid
        
        # Join a room specific to this tenant
        await self.sio.enter_room(sid, tenant_id)
        
        logger.info(f"Tenant '{tenant_id}' connected. SID: {sid}")
        await self.sio.emit('status', {'msg': 'Connected to K24 Cloud', 'tenant_id': tenant_id}, room=sid)

    async def disconnect(self, sid):
        """Handle disconnection"""
        # Find tenant_id for this sid
        disconnected_tenant = None
        for tid, s in self.active_tenants.items():
            if s == sid:
                disconnected_tenant = tid
                break
        
        if disconnected_tenant:
            del self.active_tenants[disconnected_tenant]
            logger.info(f"Tenant '{disconnected_tenant}' disconnected. SID: {sid}")

    async def send_command(self, tenant_id: str, event: str, payload: Dict[str, Any], timeout: int = 15) -> Any:
        """
        Send a command to a specific tenant's Tally Agent and await response.
        """
        if tenant_id not in self.active_tenants:
            logger.warning(f"Cannot send command: Tenant '{tenant_id}' not connected.")
            return None
            
        req_id = f"req_{uuid.uuid4().hex[:8]}"
        payload['id'] = req_id
        
        # Create Future
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self.pending_requests[req_id] = future
        
        try:
            logger.info(f"Sending '{event}' to Tenant '{tenant_id}' (ID: {req_id})")
            logger.info(f"DEBUG: Confirmed Emitting Socket Event: {event} with payload keys: {list(payload.keys())}")
            await self.sio.emit(event, payload, room=tenant_id)
            
            # Wait for response
            logger.info(f"⏳ Waiting for response (Timeout: {timeout}s)...")
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"❌ Command timed out for {req_id}")
            if req_id in self.pending_requests:
                del self.pending_requests[req_id]
            return None
        except Exception as e:
            logger.error(f"❌ Send Command Error: {e}")
            if req_id in self.pending_requests:
                del self.pending_requests[req_id]
            return None

    async def handle_tally_response(self, sid, data):
        """
        Handle response from Client Agent.
        """
        req_id = data.get('req_id') # TallyAgent echoes 'id' as 'req_id'
        logger.info(f"Received Tally Response from {sid}: {data}") # DEBUG: Log full payload
        
        if req_id and req_id in self.pending_requests:
            future = self.pending_requests[req_id]
            if not future.done():
                future.set_result(data)
            del self.pending_requests[req_id]

    def set_main_loop(self, loop):
        """Set the main asyncio loop for thread-safe operations"""
        self.main_loop = loop
        logger.info(f"SocketManager: Main Loop captured: {loop}")

    async def _awaitable_command(self, tenant_id: str, event: str, payload: Dict[str, Any], timeout: int):
        """Wrapper to call send_command and return result"""
        return await self.send_command(tenant_id, event, payload, timeout)

    def execute_sync(self, tenant_id: str, event: str, payload: Dict[str, Any], timeout: int = 15) -> Any:
        """
        Thread-safe execution for Sync contexts (Celery Workers/Threads).
        Blocks safely until the async command returns or timeouts.
        """
        if not hasattr(self, 'main_loop') or not self.main_loop:
             logger.error("Main loop not set in SocketManager. Cannot execute sync.")
             return None
             
        # Create a concurrent.futures.Future to bridge Sync world to Async world
        import concurrent.futures
        future = concurrent.futures.Future()

        async def _bridge():
            try:
                result = await self.send_command(tenant_id, event, payload, timeout)
                future.set_result(result)
            except Exception as e:
                future.set_exception(e)

        # Schedule the bridge on the main loop
        asyncio.run_coroutine_threadsafe(_bridge(), self.main_loop)
        
        try:
            # Block this thread until result is ready
            return future.result(timeout=timeout + 2)
        except Exception as e:
            logger.error(f"Sync Execution Failed: {e}")
            return None

# Global Instance
socket_manager = K24SocketManager()
