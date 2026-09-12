import traceback
import dashboard.app as a

try:
    result = a.load_dashboard(0, 'CUST001')
    print(type(result))
    print(result)
except Exception:
    traceback.print_exc()
