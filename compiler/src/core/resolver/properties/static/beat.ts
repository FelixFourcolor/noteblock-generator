import type { Beat as T_Beat } from "#schema/@";
import { Static } from "../static.js";

export const Beat = Static<T_Beat>({ Default: 4 });
