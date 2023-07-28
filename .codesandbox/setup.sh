WORKSPACE="/workspace"

# Install python dependencies
poetry update && poetry install -E report

# Install frontend dependencies for pipen-report
pipen report update

# Install frontend dependencies
cd $WORKSPACE/pipen_board/frontend
npm install

cd $WORKSPACE
