# Frugality Bash Completion

_frug() {
  local cur prev opts
  COMPREPLY=()
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"
  
  opts="start stop status update doctor version help agent"
  start_opts="--agentic -a --light"
  agent_opts="status models refresh"
  
  case "${COMP_CWORD}" in
    1)
      COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
      return 0
      ;;
    2)
      case "${prev}" in
        start)
          COMPREPLY=($(compgen -W "${start_opts}" -- ${cur}))
          return 0
          ;;
        agent)
          COMPREPLY=($(compgen -W "${agent_opts}" -- ${cur}))
          return 0
          ;;
      esac
      ;;
  esac
  
  COMPREPLY=($(compgen -f -- ${cur}))
  return 0
}

complete -F _frug frug
complete -F _frug node
complete -F _frug npm run

complete -F _frug frug-start
complete -F _frug frug-stop
complete -F _frug frug-status
complete -F _frug frug-agent
complete -F _frug frug-now
complete -F _frug frug-doctor
