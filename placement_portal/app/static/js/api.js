// Minimal fetch wrapper. Sessions (Flask-Login) are cookie-based,
// so we just need credentials: 'include' on every request.
const api = {
  async request(method, url, body) {
    const res = await fetch(url, {
      method,
      credentials: "include",
      headers: body ? { "Content-Type": "application/json" } : {},
      body: body ? JSON.stringify(body) : undefined,
    });

    // Try to parse JSON. If the server returned an HTML error page (e.g. a
    // Flask 500), json() will fail — fall back to text so we can surface the
    // real HTTP status instead of a useless "Request failed".
    let data;
    try {
      data = await res.json();
    } catch {
      if (!res.ok) {
        throw new Error(`Server error ${res.status} — check the Flask terminal for the traceback.`);
      }
      return {};
    }

    if (!res.ok) {
      throw new Error(data.error || `Request failed (${res.status})`);
    }
    return data;
  },
  get(url)          { return this.request("GET",    url);       },
  post(url, body)   { return this.request("POST",   url, body); },
  put(url, body)    { return this.request("PUT",    url, body); },
  patch(url, body)  { return this.request("PATCH",  url, body); },
};
