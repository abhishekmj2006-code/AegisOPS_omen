import sys
import os

# Add central-saas directory to sys.path for test discovery
saas_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if saas_dir not in sys.path:
    sys.path.insert(0, saas_dir)
