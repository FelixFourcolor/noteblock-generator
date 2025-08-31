import type { Beat as T_Beat } from "#lib/schema/types/@";
import { Static } from "../static.js";

export const Beat = Static<T_Beat>({ Default: 4 });
