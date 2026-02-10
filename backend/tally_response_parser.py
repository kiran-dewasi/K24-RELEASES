import xml.etree.ElementTree as ET
import logging
from typing import Dict, Any, List, Optional
from backend.tally_live_update import TallyResponse

logger = logging.getLogger("tally_response_parser")

def parse_tally_response(xml_response: str) -> TallyResponse:
    """
    Parses the raw XML response from Tally and determines success/failure.
    Returns a TallyResponse object.
    """
    if not xml_response:
        return TallyResponse(
            raw_xml="",
            status="Empty Response",
            errors=["Empty response from Tally"]
        )

    try:
        # Clean up potential encoding issues or whitespace
        xml_response = xml_response.strip()
        root = ET.fromstring(xml_response)
        
        # 1. Check for LINEERROR (Common Tally Error Tag)
        errors = []
        line_errors = root.findall(".//LINEERROR")
        if line_errors:
            for error in line_errors:
                if error.text:
                    errors.append(error.text.strip())
        
        # Also check for ERROR tag
        generic_errors = root.findall(".//ERROR")
        if generic_errors:
             for error in generic_errors:
                if error.text:
                    errors.append(error.text.strip())

        # 2. Check for Success Counts
        created = 0
        altered = 0
        deleted = 0
        errors_count = 0
        
        created_node = root.find(".//CREATED")
        if created_node is not None and created_node.text: created = int(created_node.text.strip() or 0)
        
        altered_node = root.find(".//ALTERED")
        if altered_node is not None and altered_node.text: altered = int(altered_node.text.strip() or 0)
        
        deleted_node = root.find(".//DELETED")
        if deleted_node is not None and deleted_node.text: deleted = int(deleted_node.text.strip() or 0)
        
        errors_count_node = root.find(".//ERRORS")
        if errors_count_node is not None and errors_count_node.text: errors_count = int(errors_count_node.text.strip() or 0)
        
        # GUID
        guid = None
        guid_node = root.find(".//GUID")
        if guid_node is not None: guid = guid_node.text
        
        last_vch_id = None
        last_vch_id_node = root.find(".//LASTVCHID")
        if last_vch_id_node is not None: last_vch_id = last_vch_id_node.text

        status = "Success"
        if errors or errors_count > 0:
            status = "Failure"
            if not errors and errors_count > 0:
                errors.append(f"Tally reported {errors_count} errors but no details provided.")
        elif created == 0 and altered == 0 and deleted == 0:
            # Check if it was ignored
            if "Ignored" in xml_response: # Simple check
                status = "Ignored"
            # Or maybe it's just a fetch response?
            # For write ops, 0/0/0 usually means ignored or failed without error.
            pass

        return TallyResponse(
            raw_xml=xml_response,
            status=status,
            errors=errors,
            created=created,
            altered=altered,
            deleted=deleted,
            guid=guid,
            last_vch_id=last_vch_id,
            is_ignored=(status == "Ignored")
        )

    except ET.ParseError as e:
        logger.error(f"Failed to parse XML: {xml_response[:200]}...")
        return TallyResponse(
            raw_xml=xml_response,
            status="XML Error",
            errors=[f"XML Parse Error: {str(e)}"]
        )
    except Exception as e:
        logger.exception("Unexpected error in parse_tally_response")
        return TallyResponse(
            raw_xml=xml_response,
            status="System Error",
            errors=[f"Unexpected Error: {str(e)}"]
        )
