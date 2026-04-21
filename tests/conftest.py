import os


# Keep IDO proxy tests deterministic: default to embedded/in-process backend
# unless a caller explicitly wants local backend auto-start.
os.environ.setdefault("ENABLE_LOCAL_IDO_BACKEND_AUTOSTART", "false")
