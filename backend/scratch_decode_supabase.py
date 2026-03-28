import jwt
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyOTY1YWYyNi0zYmRkLTQ3NjgtYTBlOS1iZDczOWVhYWU3NjgiLCJ0ZW5hbnRfaWQiOiJURU5BTlQtMjk2NWFmMjYiLCJleHAiOjE3NzQ2MjA5NTl9.bvpKhVNQvYUSSfyuv5Lg-TodLpsbWoHiEt9K8joL9UI"
SECRET = "Ui2nBu0na7VHSRMUoJYgCsd6qSoPUq7HI4Fn-U7bw_uk506pTKfTJNBtDgd778IQ"
try:
    decoded = jwt.decode(TOKEN, SECRET, algorithms=["HS256"])
    print("DECODED OK:", decoded)
except Exception as e:
    print("DECODE FAILED:", type(e).__name__, str(e))
