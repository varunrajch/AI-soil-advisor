import type { ExtractResult, Explanation, Health, Meta, Plan, PlanRequest } from "./types";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit, as: "json" | "blob" = "json"): Promise<T> {
  const res = await fetch(`/api${path}`, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* body was not JSON */
    }
    throw new ApiError(res.status, detail);
  }
  return (as === "blob" ? res.blob() : res.json()) as Promise<T>;
}

const post = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  health: () => request<Health>("/health"),
  meta: () => request<Meta>("/meta"),
  plan: (req: PlanRequest) => request<Plan>("/plan", post(req)),
  explain: (req: PlanRequest) => request<Explanation>("/explain", post(req)),
  speak: (req: PlanRequest) => request<Blob>("/speak", post(req), "blob"),
  extract: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<ExtractResult>("/extract", { method: "POST", body: form });
  },
};
