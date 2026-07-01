SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

trap 'kill %1 %2' SIGINT

uvicorn mailextractor.backend.main:app --reload &
cd "$SCRIPT_DIR/../frontend" && npm run dev &

wait