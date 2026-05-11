from app import mcp

import tools.activities  # noqa: F401
import tools.health      # noqa: F401
import tools.training    # noqa: F401
import tools.profile     # noqa: F401
import tools.workouts    # noqa: F401
import tools.swimming    # noqa: F401

if __name__ == "__main__":
    mcp.run()
