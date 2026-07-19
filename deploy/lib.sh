##########
# lib.sh #
##########
#
# lib.sh contains helpers for scripts in this repository.

function errorable() {
	"$@"
	local rc=$?

	if [[ "$rc" != 0 ]]; then
		final_rc=$((final_rc + 1))
	fi
}

final_rc=0
