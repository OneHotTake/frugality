# Frugality Zsh Completion

frug_commands=(
  'start:Start the Frugality system'
  'stop:Stop the Frugality system'
  'status:Show system status'
  'update:Update model configurations'
  'doctor:Diagnose and fix issues'
  'version:Show version'
  'help:Show help'
  'agent:Agentic mode commands'
)

frug_start_options=(
  '--agentic:Start in agentic mode (Claude as router)'
  '-a:Short for --agentic'
  '--light:Start in light mode'
)

frug_agent_options=(
  'status:Show agentic mode status'
  'models:List cached models'
  'refresh:Refresh model cache'
)

_frug() {
  local -a commands
  commands=(${frug_commands})
  
  local -a start_opts
  start_opts=(${frug_start_options})
  
  local -a agent_opts
  agent_opts=(${frug_agent_options})
  
  _describe 'command' commands
}

_frug_start() {
  _describe 'option' start_opts
}

_frug_agent() {
  _describe 'command' agent_opts
}

case "${words[1]}" in
  start)
    _frug_start
    ;;
  agent)
    _frug_agent
    ;;
  *)
    _frug
    ;;
esac

compdef _frug frug
compdef _frug frug-start
compdef _frug frug-stop
compdef _frug frug-status
compdef _frug frug-agent
compdef _frug frug-now
