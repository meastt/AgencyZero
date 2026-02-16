#!/bin/bash
# Install OpenClaw if not present
if ! command -v openclaw &> /dev/null
then
    curl -fsSL https://openclaw.ai/install.sh | bash
fi

# Authenticate and Start Gateway
openclaw agents add seo_manager --workspace ./agents/seo_manager
openclaw gateway start