_lib_sh_dir=$(dirname "${BASH_SOURCE[0]}")

function source_venv() {
	if [[ -z "$VIRTUAL_ENV" || "$VIRTUAL_ENV" != "$(cd "$_lib_sh_dir"; printf '%s/.venv' "$PWD")" ]]; then
		source "$_lib_sh_dir/../.venv/bin/activate"
	fi
}
