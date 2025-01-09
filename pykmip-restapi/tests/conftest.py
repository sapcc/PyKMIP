import os
import sys

# Add the pykmip-restapi directory to the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Add the root project directory to the python path (for kmip module)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
