import { useEffect, useState } from "react";
import { getOpenApi } from "./api/examples";

export default function App() {
  const [status, setStatus] = useState<"idle" | "loading" | "ok" | "error">("idle");
  const [size, setSize] = useState<number | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setStatus("loading");
        const data = await getOpenApi();
        const bytes = new Blob([JSON.stringify(data)]).size;
        setSize(bytes);
        setStatus("ok");
      } catch (error) {
        console.error("OpenAPI fetch failed", error);
        setStatus("error");
      }
    })();
  }, []);

  return (
    <div style={{ maxWidth: 720, margin: "40px auto", padding: 16 }}>
      <h1>PulsePlate — Dev Smoke</h1>
      <p>
        Proxy to FastAPI via <code>/openapi.json</code>
      </p>
      <p>
        Status: <strong>{status}</strong>
        {size ? ` (${size} bytes)` : ""}
      </p>
    </div>
  );
}
