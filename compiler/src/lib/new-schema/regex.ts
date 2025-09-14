export type Pattern = string | RegExp;

export function re(...patterns: Pattern[]) {
	return regex(join(patterns.map(unwrap), ""));
}

export namespace re {
	export function union(...patterns: Pattern[]) {
		return regex(join(patterns.map(unwrap), "|"));
	}

	export function token(tok: Pattern, sep?: string) {
		sep = sep ? `\\s*${sep}\\s*` : "\\s*";
		return re(sep, group(unwrap(tok)), sep);
	}

	export function and(...patterns: Pattern[]) {
		if (patterns.length === 0) {
			return regex("");
		}
		if (patterns.length === 1) {
			return regex(unwrap(patterns[0]!));
		}

		const lookaheads = patterns
			.slice(0, -1)
			.map(unwrap)
			.map((s) => `(?=${s})`);
		const lastPattern = unwrap(patterns[patterns.length - 1]!);

		return regex(lookaheads.join("") + lastPattern);
	}

	export function peat(
		pattern: Pattern,
		options: {
			atLeast: number;
			separator: string;
			wrapper?: string | readonly [string, string];
		},
	) {
		const { atLeast, separator, wrapper = "" } = options;

		const openWrapper = Array.isArray(wrapper) ? wrapper[0] : wrapper;
		const closeWrapper = Array.isArray(wrapper) ? wrapper[1] : wrapper;

		return re(
			re.token(openWrapper),
			pattern,
			re(re.token(separator), pattern, `{${Math.max(0, atLeast)},}`),
			"*",
			re.token(closeWrapper),
		);
	}
}

const group = (s: string) => `(${s})`;
function unwrap(p: Pattern) {
	if (p instanceof RegExp) {
		return p.source;
	}
	return p;
}

function join(tokens: string[], by: string): string {
	if (tokens.length === 0) {
		return "";
	}
	if (tokens.length === 1) {
		return tokens[0]!;
	}
	return tokens.map(group).join(by);
}

function regex(token: string) {
	return new RegExp(token, "i");
}
