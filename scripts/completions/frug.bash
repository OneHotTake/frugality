#!/bin/bash
# Bash completions for frugal-claude and frugal-opencode

_frugal_claude() {
    local cur prev
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    case "${prev}" in
        frugal-claude)
            COMPREPLY=($(compgen -W "--help --version --print-only" -- ${cur}))
            return 0
            ;;
    esac
}

_frugal_opencode() {
    local cur prev
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    case "${prev}" in
        frugal-opencode)
            COMPREPLY=($(compgen -W "--help --version" -- ${cur}))
            return 0
            ;;
    esac
}

complete -F _frugal_claude frugal-claude
complete -F _frugal_opencode frugal-opencode
