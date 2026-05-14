# isort: skip_file
from app import mcp  # noqa: F401

import tools.activities  # noqa: F401
import tools.calendar    # noqa: F401
import tools.health      # noqa: F401
import tools.plans       # noqa: F401
import tools.profile     # noqa: F401
import tools.running     # noqa: F401
import tools.strength    # noqa: F401
import tools.swimming    # noqa: F401
import tools.training    # noqa: F401
import resources         # noqa: F401
import prompts           # noqa: F401

if __name__ == "__main__":
    mcp.run()
