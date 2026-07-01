SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    echo "This script has to be SOURCED."
    exit 1
fi

VENV=$(realpath "$SCRIPT_DIR/../.venv")
if [ ! -d "$VENV" ]; then
    echo "Missing python environment $VENV" >&2
    return 1
fi

NENV=$(realpath "$SCRIPT_DIR/../.nenv")
if [ ! -d "$NENV" ]; then
    echo "Missing node environment $NENV" >&2
    echo "Install: nodeenv -n 24.14.1 .nenv" >&2
    return 1
fi

source $VENV/bin/activate
source $NENV/bin/activate
