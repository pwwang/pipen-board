WORKSPACE="/workspace"

# Install python dependencies
poetry update && poetry install -E report -E diagram -E filters

# Install frontend dependencies for pipen-report
pipen report update

# Install frontend dependencies
cd $WORKSPACE/pipen_board/frontend
npm install

cd $WORKSPACE

# Install whichpy
WHICHPY="https://gist.githubusercontent.com/pwwang/879966128b0408c2459eb0a0b413fa69/raw/2f2573d191edec1937a2bf0873aa33a646b5ef29/whichpy.fish"
mkdir -p ~/.config/fish/functions/
wget $WHICHPY -O ~/.config/fish/functions/whichpy.fish
