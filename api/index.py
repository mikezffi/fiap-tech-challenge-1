from mangum import Mangum
from api.api_v1 import app

handler = Mangum(app)