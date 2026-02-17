from fastapi import FastAPI
import logging
from . import backhaul
from . import ap
from . import ups
from . import rpc
from . import switch
from . import device_info
from . import ping
from . import mikrotik
from . import site_info
from . import waveconfig
from . import config7250

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app = FastAPI()
app.include_router(backhaul.app)
app.include_router(ap.app)
app.include_router(ups.app)
app.include_router(rpc.app)
app.include_router(switch.app)
app.include_router(device_info.app)
app.include_router(ping.app)
app.include_router(mikrotik.app)
app.include_router(site_info.app)
app.include_router(waveconfig.app)
app.include_router(config7250.app)