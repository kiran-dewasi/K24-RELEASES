
import asyncio
import json
import os
import uuid
import requests
from datetime import datetime
from database.supabase_client import supabase
from database.repository import TaskRepository, AuditRepository
from database import SessionLocal, Voucher, Ledger, StockItem, InventoryEntry

# Async Helper
def run_async(coro):
    """Helper to run async code in sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    return loop.run_until_complete(coro)

# Helper Functions for WhatsApp
def get_or_create_user_for_phone(phone_number: str):
    """Link WhatsApp number to existing user or create temp user"""
    if not supabase:
        return "default_whatsapp_user"
        
    # Check mapping
    try:
        result = supabase.table("user_whatsapp_mapping").select("user_id").eq("whatsapp_phone", phone_number).execute()
        
        if result.data:
            return result.data[0]["user_id"]
    except Exception:
        pass
    
    # Create temp user
    user_id = f"whatsapp_{phone_number}"
    
    try:
        supabase.table("user_whatsapp_mapping").insert({
            "whatsapp_phone": phone_number,
            "user_id": user_id,
            "created_at": datetime.now().isoformat()
        }).execute()
    except Exception as e:
        # Ignore duplicate error if race condition
        pass
        
    return user_id

def send_whatsapp_message(phone_number: str, message_text: str):
    """Send message via WhatsApp API"""
    phone_id = os.getenv('WHATSAPP_BUSINESS_PHONE_ID')
    token = os.getenv('WHATSAPP_API_TOKEN')
    
    if not phone_id or not token:
        print("Missing WhatsApp Credentials")
        return
        
    url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    body = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {"body": message_text}
    }

    try:
        response = requests.post(url, json=body, headers=headers, timeout=10)
        
        # Log Sent
        if supabase:
            try:
                supabase.table("whatsapp_sent_messages").insert({
                    "phone": phone_number,
                    "message_text": message_text,
                    "api_status": response.status_code,
                    "api_response": response.json(),
                    "sent_at": datetime.now().isoformat()
                }).execute()
            except: 
                pass
        
        if response.status_code != 200:
             print(f"WhatsApp API Error: {response.text}")
             # Optionally store error
             if supabase:
                 try:
                     supabase.table("whatsapp_send_errors").insert({
                        "phone": phone_number,
                         "message_text": message_text,
                         "error": response.text
                     }).execute()
                 except:
                     pass
        
        return response.json()
        
    except Exception as e:
        if supabase:
             try:
                 supabase.table("whatsapp_send_errors").insert({
                "phone": phone_number,
                 "message_text": message_text,
                 "error": str(e)
                 }).execute()
             except:
                 pass
        raise

def invoke_agent_with_context(user_id: str, user_message: str, source_pipeline: str):
    """
    Reuse existing agent invocation from agent
    """
    from agent import agent
    
    async def call_agent():
        response = await agent.ainvoke({
            "messages": [{"role": "user", "content": user_message}],
            "thread_id": user_id, 
            "user_id": user_id
        })
        return response.get("output", "No response")
    
    return run_async(call_agent())

def logic_process_whatsapp_message(from_phone, message_text, message_id, webhook_timestamp):
    """
    Core logic for processing WhatsApp message.
    Decoupled from Celery task wrapper.
    """
    if not supabase:
        print("Supabase not configured, skipping WhatsApp processing")
        return

    # 1. Store raw message
    try:
        raw_msg = {
            "from_phone": from_phone,
            "message_text": message_text,
            "message_id": message_id,
            "processed": False
        }
        supabase.table("whatsapp_raw_messages").insert(raw_msg).execute()
    except Exception as e:
        print(f"Duplicate or DB Error: {e}")
        return 

    # 2. Get User
    user_id = get_or_create_user_for_phone(from_phone)
    
    # 3. Store incoming message in main chat
    try:
            supabase.table("messages").insert({
            "user_id": user_id, 
            "role": "user",
            "content": message_text,
            "source_pipeline": "WHATSAPP",
            "whatsapp_from_phone": from_phone,
            "whatsapp_message_id": message_id
            }).execute()
    except Exception as e:
            print(f"Failed to log to messages: {e}")
            
    # 4. Invoke Agent
    response_text = invoke_agent_with_context(user_id, message_text, "WHATSAPP")
    
    # 5. Send Response
    send_whatsapp_message(from_phone, response_text)
    
    # 6. Log Response
    try:
            supabase.table("messages").insert({
            "user_id": user_id, 
            "role": "assistant",
            "content": response_text,
            "source_pipeline": "WHATSAPP",
            "whatsapp_from_phone": from_phone
            }).execute()
    except:
        pass
        
    # 7. Mark Processed
    supabase.table("whatsapp_raw_messages").update({
        "processed": True, 
        "processed_at": datetime.now().isoformat()
    }).eq("message_id", message_id).execute()

async def logic_create_ledger_async(ledger_data: dict, user_id: str = "agent", 
                      thread_id: str = None, triggered_by_message_id: str = None):
    try:
        task_id = str(uuid.uuid4())
        print(f"\n{'='*70}")
        print(f"ðŸ”„ ASYNC LOGIC: create_ledger")
        print(f"   Task ID: {task_id}")
        print(f"   Ledger: {ledger_data.get('name')}")
        print(f"{'='*70}\n")
        
        task_repo = TaskRepository()
        audit_repo = AuditRepository()
        
        await task_repo.create_task_progress(celery_task_id=task_id, thread_id=thread_id, operation="create_ledger")
        await task_repo.update_task_progress(celery_task_id=task_id, status="processing", progress_percent=10, current_step="connecting_to_tally")
        
        company = os.getenv("TALLY_COMPANY", "Krishasales")
        
        parent_group = ledger_data.get("parent")
        if not parent_group:
             parent_group = "Sundry Debtors" if ledger_data.get('type') == 'customer' else "Sundry Creditors"

        fields = {
            "Partygstregistrationnumber": ledger_data.get("gst"),
            "Partygstregistrationtype": "Regular" if ledger_data.get("gst") else "Unregistered",
            "Address": ledger_data.get("address"),
            "Email": ledger_data.get("email"),
            "Mobile": ledger_data.get("phone")
        }
        fields = {k: v for k, v in fields.items() if v is not None}

        # Use new Async Helper
        from tally_live_update import create_ledger_async as _create_ledger_direct_async
        
        response = await _create_ledger_direct_async(company=company, ledger_name=ledger_data.get("name"), parent=parent_group, fields=fields)

        if not response.success:
            raise Exception(f"Tally Error: {response.error_details}")

        result = {"status": "created", "ledger_name": ledger_data.get("name"), "tally_response": response.to_dict(), "task_id": task_id}
        
        # --- PERSISTENCE: Save/Update Local DB ---
        try:
             db = SessionLocal()
             l_name = ledger_data.get("name")
             existing = db.query(Ledger).filter(Ledger.name == l_name).first() # Add tenant_id filter if/when available
             
             if not existing:
                  new_l = Ledger(
                      tenant_id="TENANT-12345",
                      name=l_name,
                      parent=parent_group,
                      gstin=ledger_data.get("gst"),
                      address=ledger_data.get("address"),
                      email=ledger_data.get("email"),
                      phone=ledger_data.get("phone")
                  )
                  db.add(new_l)
                  db.commit()
                  print(f"DEBUG: Saved new ledger '{l_name}' to local DB.")
             else:
                  # Update fields
                  if ledger_data.get("gst"): existing.gstin = ledger_data.get("gst")
                  if ledger_data.get("address"): existing.address = ledger_data.get("address")
                  if ledger_data.get("email"): existing.email = ledger_data.get("email")
                  if ledger_data.get("phone"): existing.phone = ledger_data.get("phone")
                  db.commit()
                  print(f"DEBUG: Updated existing ledger '{l_name}' in local DB.")
             db.close()
        except Exception as e:
             print(f"DEBUG: Failed to persist ledger locally: {e}")
        
        await audit_repo.log_operation(table_name="ledgers", record_id=ledger_data.get('name'), operation='CREATE', executed_by=user_id, thread_id=thread_id, triggered_by_message_id=triggered_by_message_id, celery_task_id=task_id, after_state=ledger_data, metadata={"tally_result": result})
        await task_repo.update_task_progress(celery_task_id=task_id, status="completed", progress_percent=100, current_step="finished", result=result)
        return result

    except Exception as e:
        task_repo = TaskRepository()
        if 'task_id' in locals():
            await task_repo.update_task_progress(celery_task_id=task_id, status="failed", progress_percent=100, error=str(e))
        raise e

async def logic_create_voucher_async(voucher_data: dict, user_id: str = "agent", 
                       thread_id: str = None, triggered_by_message_id: str = None):
    print(f"DEBUG: Starting Logic for {voucher_data}")
    try:
        task_id = str(uuid.uuid4())
        print(f"\n{'='*70}")
        print(f"ðŸ”„ ASYNC LOGIC: create_voucher")
        print(f"   Task ID: {task_id}")
        print(f"   Type: {voucher_data.get('type')}")
        print(f"{'='*70}\n")
        
        task_repo = TaskRepository()
        audit_repo = AuditRepository()
        
        await task_repo.create_task_progress(celery_task_id=task_id, thread_id=thread_id, operation="create_voucher")
        await task_repo.update_task_progress(celery_task_id=task_id, status="processing", progress_percent=10, current_step="connecting_to_tally")
        
        company = os.getenv("TALLY_COMPANY", "Krishasales")
        date_str = voucher_data.get("date", "").replace("-", "")
        if not date_str:
            date_str = datetime.now().strftime("%Y%m%d")
            
        voucher_fields = {
            "Date": date_str,
            "PartyLedgerName": voucher_data.get("party"),
            "Narration": voucher_data.get("narration") or voucher_data.get("description") or voucher_data.get("descripttion") or ""
        }
        
        items = voucher_data.get("items", [])
        if not items:
             amount = voucher_data.get('amount')
             if amount:
                 v_type = voucher_data.get('type', 'Sales')
                 is_debit_leg = False 
                 ledger_leg = "Sales Account"
                 if v_type == 'Receipt':
                     # Two Legs for Receipt
                     items.append({"ledger": "Cash", "amount": amount, "is_debit": True})
                     party_leg = voucher_data.get("party")
                     items.append({"ledger": party_leg, "amount": amount, "is_debit": False})
                 elif v_type == 'Payment':
                     # Two Legs for Payment
                     items.append({"ledger": "Cash", "amount": amount, "is_debit": False})
                     party_leg = voucher_data.get("party")
                     items.append({"ledger": party_leg, "amount": amount, "is_debit": True})
                 elif v_type == 'Sales':
                     # Sales Logic usually: Party Dr, Sales Cr
                     party_leg = voucher_data.get("party")
                     items.append({"ledger": party_leg, "amount": amount, "is_debit": True})
                     items.append({"ledger": "Sales Account", "amount": amount, "is_debit": False})
                 else:
                     # Fallback (Single Leg - Might Fail)
                     items = [{"ledger": ledger_leg, "amount": amount, "is_debit": is_debit_leg}]

        from tally_live_update import create_voucher_async as _create_voucher_direct_async
        from tally_live_update import create_ledger_async as _create_ledger_direct_async

        # --- PERSISTENCE: Check Local DB First ---
        party_name = voucher_data.get("party")
        ledger_db_id = None
        
        if party_name:
             party_name = party_name.strip()
             v_type_chk = voucher_data.get("type", "Sales")
             parent_grp = "Sundry Creditors" if v_type_chk in ["Payment", "Purchase"] else "Sundry Debtors"

             # Check Local DB
             db = SessionLocal()
             try:
                 # Check if exists (Case Insensitive Search might be better, but exact for now)
                 existing_ledger = db.query(Ledger).filter(Ledger.name == party_name).first()
                 
                 if existing_ledger:
                     print(f"DEBUG: Found existing ledger via Local Persistence: {existing_ledger.name} (ID: {existing_ledger.id})")
                     ledger_db_id = existing_ledger.id
                 else:
                     # Create Local Ledger
                     print(f"DEBUG: Ledger '{party_name}' NOT found locally. Auto-creating...")
                     
                     new_ledger = Ledger(
                         tenant_id="TENANT-12345", # Match the tenant used in Voucher
                         name=party_name,
                         parent=parent_grp,
                         opening_balance=0.0, 
                         # Try to extract contact info if embedded in voucher_data somehow, or default
                         gstin=voucher_data.get("partynumber") or voucher_data.get("gstin"),
                         address=voucher_data.get("address"),
                         email=voucher_data.get("email"),
                         phone=voucher_data.get("phone")
                     )
                     db.add(new_ledger)
                     db.commit()
                     db.refresh(new_ledger)
                     ledger_db_id = new_ledger.id
                     print(f"DEBUG: Created new Local Ledger: {new_ledger.name} (ID: {new_ledger.id})")
             except Exception as e:
                 print(f"DEBUG: Local Persistence Check Failed: {e}")
             finally:
                 db.close()

             # --- COMPATIBILITY FIX: Ensure Party Ledger Exists in Tally ---
             # We still ensure it exists in Tally to prevent Voucher rejection
             print(f"DEBUG: Auto-Creating Ledger '{party_name}' (Parent: {parent_grp}) check...")
             led_resp = await _create_ledger_direct_async(company=company, ledger_name=party_name, parent=parent_grp, fields={"ISBILLWISEON": "No"})
             
             if not led_resp.success:
                  err_lower = led_resp.error_details.lower()
                  if "already exists" not in err_lower and "duplicate" not in err_lower:
                       print(f"DEBUG: Ledger Creation Warning: {led_resp.error_details}")
                  else:
                       print(f"DEBUG: Ledger '{party_name}' already exists (OK).")
             else:
                  print(f"DEBUG: Ledger '{party_name}' Created Successfully.")

        print("DEBUG: Calling tally.post_to_tally (via async wrapper)...")
        response = await _create_voucher_direct_async(company=company, voucher_type=voucher_data.get("type", "Sales"), voucher_fields=voucher_fields, line_items=items)

        if not response.success:
            raise Exception(f"Tally Error: {response.error_details}")

        result = {"status": "created", "voucher_type": voucher_data.get("type"), "tally_response": response.to_dict() if hasattr(response.tally_response, 'to_dict') else response.tally_response, "task_id": task_id}
        
        # --- PERSIST TO VOUCHERS TABLE (SYNC TO WEB UI) ---
        try:
             # Basic mapping
             v_date = date_str
             if len(v_date) == 8: # YYYYMMDD -> YYYY-MM-DD
                 v_date = f"{v_date[:4]}-{v_date[4:6]}-{v_date[6:]}"
                 
             calc_amount = voucher_data.get("amount", 0.0)
             if not calc_amount and items:
                 total = sum(float(i.get('amount', 0)) for i in items if not i.get('is_debit', False)) 
                 if total == 0:
                      total = sum(float(i.get('amount', 0)) for i in items if i.get('is_debit', False))
                 calc_amount = total

             db = SessionLocal()
             try:
                 v_num_cand = "TEMP-TASK-" + task_id[:6]
                 new_v = Voucher(
                     tenant_id="TENANT-12345",
                     voucher_number=v_num_cand, 
                     date=datetime.strptime(v_date, "%Y-%m-%d"),
                     party_name=voucher_data.get("party"),
                     amount=calc_amount,
                     voucher_type=voucher_data.get("type"),
                     sync_status="SYNCED",
                     narration=voucher_data.get("narration", ""),
                     source="whatsapp_task",
                     ledger_id=ledger_db_id
                 )
                 db.add(new_v)
                 db.commit()
                 db.refresh(new_v) # Get ID
                 print(f"DEBUG: Saved voucher to DB: {new_v.voucher_number} (ID: {new_v.id})")

                 # --- INVENTORY PERSISTENCE ---
                 # Check if we have stock items in the payload
                 raw_items = voucher_data.get("items", [])
                 for row in raw_items:
                     # Heuristic: If it has 'qty' or 'quantity', it's likely a Stock Item
                     item_name = row.get("item") or row.get("name")
                     qty = float(row.get("qty") or row.get("quantity") or 0)
                     
                     if item_name and qty != 0:
                         # 1. Ensure Stock Master Exists
                         s_item = db.query(StockItem).filter(StockItem.name == item_name).first() # Add tenant check later
                         if not s_item:
                             print(f"DEBUG: Auto-Creating Stock Item: {item_name}")
                             s_item = StockItem(
                                 tenant_id="TENANT-12345",
                                 name=item_name,
                                 closing_balance=0.0 # Will update
                             )
                             db.add(s_item)
                             db.commit()
                             db.refresh(s_item)
                         
                         # 2. Determine Direction (Inward/Outward) based on Voucher Type
                         # Sales -> Outward (-), Purchase -> Inward (+)
                         # Returns -> Opposite
                         v_type = voucher_data.get("type", "Sales")
                         is_inward = False
                         if v_type in ["Purchase", "Credit Note", "Receipt Note"]:
                             is_inward = True
                         elif v_type in ["Sales", "Debit Note", "Delivery Note"]:
                             is_inward = False
                         
                         # 3. Create Inventory Entry
                         inv_entry = InventoryEntry(
                             tenant_id="TENANT-12345",
                             voucher_id=new_v.id,
                             item_id=s_item.id,
                             actual_qty=qty,
                             billed_qty=qty,
                             rate=float(row.get("rate") or 0),
                             amount=float(row.get("amount") or 0),
                             is_inward=is_inward
                         )
                         db.add(inv_entry)
                         
                         # 4. Update Stock Level
                         if is_inward:
                             s_item.closing_balance += qty
                         else:
                             s_item.closing_balance -= qty
                             
                         db.commit()
                         print(f"DEBUG: Stock Updated for {item_name}: New Bal {s_item.closing_balance}")

             except Exception as sa_err:
                 print(f"DEBUG: SQLAlchemy Insert Failed: {sa_err}")
                 db.rollback()
             finally:
                 db.close()

        except Exception as db_err:
             print(f"DEBUG: Failed to save to vouchers table: {db_err}")

        await audit_repo.log_operation(table_name="vouchers", record_id=f"{voucher_data.get('type')}-{voucher_data.get('party')}", operation='CREATE', executed_by=user_id, thread_id=thread_id, triggered_by_message_id=triggered_by_message_id, celery_task_id=task_id, after_state=voucher_data, metadata={"tally_result": result})
        await task_repo.update_task_progress(celery_task_id=task_id, status="completed", progress_percent=100, current_step="finished", result=result)
        return result

    except Exception as e:
        print(f"DEBUG: Logic Error: {e}")
        print(f"âŒ CRITICAL TASK ERROR: {e}")
        task_repo = TaskRepository()
        if 'task_id' in locals():
            await task_repo.update_task_progress(celery_task_id=task_id, status="failed", progress_percent=100, error=str(e))
        raise e

