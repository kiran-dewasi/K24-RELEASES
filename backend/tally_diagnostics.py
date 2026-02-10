import requests
import os
from dataclasses import dataclass
from typing import List
from backend.tally_live_update import TallyXMLBuilder, post_to_tally

TALLY_URL = os.getenv("TALLY_URL", "http://localhost:9000")

@dataclass
class DiagnosticResult:
    timestamp: str
    check_name: str
    status: str  # "OK", "WARNING", "ERROR"
    details: str
    remediation: str

class TallyDiagnostics:
    @staticmethod
    def check_tally_running() -> DiagnosticResult:
        import datetime
        timestamp = datetime.datetime.now().isoformat()
        try:
            # Tally usually responds to GET / with some info or at least connects
            response = requests.get(TALLY_URL, timeout=5)
            # Tally might return data or just be reachable. 200 OK is good.
            if response.ok or response.status_code == 200:
                return DiagnosticResult(timestamp, "Tally Running Check", "OK", f"Tally responding at {TALLY_URL}", "")
            else:
                 return DiagnosticResult(timestamp, "Tally Running Check", "WARNING", f"Tally found but status {response.status_code}", "Check Tally Server settings.")
        except requests.exceptions.ConnectionError:
            return DiagnosticResult(timestamp, "Tally Running Check", "ERROR", f"Could not connect to {TALLY_URL}", "Start Tally ERP/Prime and ensure it is listening on port 9000.")
        except requests.exceptions.Timeout:
             return DiagnosticResult(timestamp, "Tally Running Check", "ERROR", "Connection timed out", "Check network configuration or Tally responsiveness.")
        except Exception as e:
            return DiagnosticResult(timestamp, "Tally Running Check", "ERROR", str(e), "Inspect logs.")

    @staticmethod
    def check_company_configured(company_name: str) -> DiagnosticResult:
        import datetime
        timestamp = datetime.datetime.now().isoformat()
        
        # Build a simple export request to check if company is active
        # Requesting "Company" object or just a simple variable
        # <ENVELOPE><HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER><BODY><EXPORTDATA><REQUESTDESC><REPORTNAME>List of Accounts</REPORTNAME><STATICVARIABLES><SVCURRENTCOMPANY>Krishasales</SVCURRENTCOMPANY></STATICVARIABLES></REQUESTDESC></EXPORTDATA></BODY></ENVELOPE>
        
        envelope = f"""<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Export Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <EXPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>List of Accounts</REPORTNAME>
                <STATICVARIABLES>
                    <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
                </STATICVARIABLES>
            </REQUESTDESC>
        </EXPORTDATA>
    </BODY>
</ENVELOPE>"""
        
        response = post_to_tally(envelope)
        
        if response.success:
            return DiagnosticResult(timestamp, f"Company {company_name} Check", "OK", "Company accessible", "")
        else:
            # If failed, it might be because company is not open
            return DiagnosticResult(timestamp, f"Company {company_name} Check", "ERROR", f"Company not responding: {response.error_details}", f"Open company '{company_name}' in Tally.")

    @staticmethod
    def check_xml_format(xml_string: str) -> DiagnosticResult:
        import datetime
        import xml.etree.ElementTree as ET
        timestamp = datetime.datetime.now().isoformat()
        try:
            ET.fromstring(xml_string)
            return DiagnosticResult(timestamp, "XML Format Check", "OK", "Valid XML", "")
        except ET.ParseError as e:
            return DiagnosticResult(timestamp, "XML Format Check", "ERROR", f"Invalid XML: {e}", "Fix XML structure.")

    @staticmethod
    def run_full_diagnostic(company_name: str) -> List[DiagnosticResult]:
        results = []
        results.append(TallyDiagnostics.check_tally_running())
        
        # Only proceed if Tally is running
        if results[0].status == "OK":
            results.append(TallyDiagnostics.check_company_configured(company_name))
        
        return results

    @staticmethod
    def print_diagnostic_report(results: List[DiagnosticResult]):
        print(f"{'CHECK':<30} | {'STATUS':<10} | {'DETAILS'}")
        print("-" * 80)
        for r in results:
            print(f"{r.check_name:<30} | {r.status:<10} | {r.details}")
            if r.status != "OK":
                print(f"  -> REMEDIATION: {r.remediation}")
