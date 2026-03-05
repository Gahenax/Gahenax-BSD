import { useState } from "react";

const layers = [
    {
        id: "orchestrator",
        label: "CAPA 3 — HTCondor Dispatcher",
        sublabel: "Orquestación distribuida",
        color: "#00ffc8",
        bg: "#001a12",
        icon: "⬡",
        description: "Distribuye curvas elípticas independientes en paralelo. Cada nodo recibe una curva, elimina el cuello de botella de RAM.",
        code: `# htcondor_dispatch.py
import htcondor
import classad

def submit_curve_jobs(curves: list):
    schedd = htcondor.Schedd()
    sub = htcondor.Submit({
        "executable": "bsd_worker.py",
        "arguments": "$(curve_id)",
        "request_memory": "8GB",
        "request_cpus": "4",
        "queue curve_id from curves.txt"
    })
    with schedd.transaction() as txn:
        cluster_id = sub.queue(txn)
    return cluster_id`,
    },
    {
        id: "orchestrator_py",
        label: "Python Orquestador",
        sublabel: "Coordinación & pipeline",
        color: "#4fc3f7",
        bg: "#001a2a",
        icon: "◈",
        description: "Recibe curvas del dispatcher, coordina el flujo entre SageMath y el motor C++, agrega resultados.",
        code: `# bsd_worker.py
from sage_engine import compute_rank_2selmer
from gmp_engine import count_points_Fp   # C++ via pybind11

def compute_bsd(a4: int, a6: int) -> dict:
    # Delegar #E(Fp) pesados a C++ GMP
    ap_values = gmp_engine.euler_product(a4, a6, primes=10000)
    
    # Rango exacto via 2-Selmer descent (SageMath)
    rank, sha_order = sage_engine.rank_descent(
        a4, a6, 
        precomputed_ap=ap_values
    )
    return {"rank": rank, "sha": sha_order, "L_value": ap_values["L"]}`,
    },
    {
        id: "sagemath",
        label: "CAPA 1 — SageMath / 2-Selmer Descent",
        sublabel: "Núcleo algebraico exacto · BASE",
        color: "#ffd54f",
        bg: "#1a1400",
        icon: "◉",
        description: "Corazón del sistema. Opera en aritmética entera exacta. Sin flotantes, sin pérdida de precisión. Calcula rango algebraico y orden de Ш.",
        code: `# sage_engine.py
from sage.all import EllipticCurve, ZZ

def rank_descent(a4: int, a6: int, precomputed_ap=None) -> tuple:
    E = EllipticCurve([ZZ(a4), ZZ(a6)])
    
    # 2-Selmer descent — aritmética exacta
    rank = E.rank(algorithm='2descent_complete')
    
    # Orden del grupo de Tate-Shafarevich
    sha = E.sha().an_numerical()
    
    # Verificación BSD: L(E,1) / (Omega * Reg * prod_cp)
    bsd_ratio = E.lseries().L1_vanishes()
    
    return rank, sha, bsd_ratio`,
    },
    {
        id: "gmp",
        label: "CAPA 2 — C++ GMP/FLINT Engine",
        sublabel: "Aceleración selectiva · #E(Fₚ) & Producto de Euler",
        color: "#ef9a9a",
        bg: "#1a0000",
        icon: "▲",
        description: "Solo toma las operaciones aritméticas más costosas. No reemplaza SageMath — le delega el trabajo pesado de conteo de puntos.",
        code: `// gmp_engine.cpp  (expuesto via pybind11)
#include <flint/fmpz.h>
#include <pybind11/pybind11.h>

// Contar puntos E(Fp) con algoritmo de Schoof-Elkies-Atkin
fmpz_t count_points_prime(fmpz_t a4, fmpz_t a6, fmpz_t p) {
    fmpz_t n;
    fmpz_init(n);
    // SEA algorithm — O(log^6 p)
    schoof_elkies_atkin(n, a4, a6, p);
    return n;
}

// Producto de Euler hasta cota N
PYBIND11_MODULE(gmp_engine, m) {
    m.def("euler_product", &euler_product_N,
          "Producto Euler L-function hasta N primos");
    m.def("count_points_Fp", &count_points_prime,
          "SEA algorithm exacto sobre Fp");
}`,
    },
];

const flow = [
    { from: "orchestrator", to: "orchestrator_py", label: "curvas batch" },
    { from: "orchestrator_py", to: "sagemath", label: "curva (a4, a6)" },
    { from: "orchestrator_py", to: "gmp", label: "#E(Fₚ) request" },
    { from: "gmp", to: "sagemath", label: "ap_values exactos" },
    { from: "sagemath", to: "orchestrator_py", label: "rank + Ш + BSD ratio" },
];

export default function Blueprint() {
    const [active, setActive] = useState(null);

    return (
        <div style={{
            background: "#07080a",
            minHeight: "100vh",
            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
            color: "#c9d1d9",
            padding: "2rem",
            position: "relative",
            overflow: "hidden",
        }}>
            {/* Background grid */}
            <div style={{
                position: "fixed", inset: 0, zIndex: 0,
                backgroundImage: `
          linear-gradient(rgba(0,255,200,0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(0,255,200,0.03) 1px, transparent 1px)
        `,
                backgroundSize: "40px 40px",
                pointerEvents: "none",
            }} />

            <div style={{ position: "relative", zIndex: 1, maxWidth: 900, margin: "0 auto" }}>
                {/* Header */}
                <div style={{ marginBottom: "2.5rem" }}>
                    <div style={{ fontSize: "0.65rem", letterSpacing: "0.3em", color: "#00ffc8", marginBottom: "0.5rem" }}>
                        GAHENAX KERNEL · BSD ENGINE · ARCHITECTURE BLUEPRINT
                    </div>
                    <h1 style={{
                        fontSize: "clamp(1.4rem, 3vw, 2rem)",
                        fontWeight: 700,
                        letterSpacing: "-0.02em",
                        color: "#f0f6fc",
                        margin: 0,
                    }}>
                        Amalgam Architecture v1.0
                    </h1>
                    <p style={{ color: "#8b949e", fontSize: "0.8rem", marginTop: "0.5rem" }}>
                        SageMath · C++ GMP/FLINT · HTCondor — haz clic en cada capa para ver el código
                    </p>
                </div>

                {/* Flow diagram */}
                <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginBottom: "2rem" }}>
                    {layers.map((layer, i) => (
                        <div key={layer.id}>
                            <div
                                onClick={() => setActive(active === layer.id ? null : layer.id)}
                                style={{
                                    background: active === layer.id ? layer.bg : "rgba(255,255,255,0.02)",
                                    border: `1px solid ${active === layer.id ? layer.color : "rgba(255,255,255,0.07)"}`,
                                    borderRadius: "6px",
                                    padding: "1rem 1.25rem",
                                    cursor: "pointer",
                                    transition: "all 0.2s",
                                    display: "flex",
                                    alignItems: "center",
                                    gap: "1rem",
                                    boxShadow: active === layer.id ? `0 0 20px ${layer.color}22` : "none",
                                }}
                            >
                                <span style={{ fontSize: "1.4rem", color: layer.color, minWidth: 28 }}>{layer.icon}</span>
                                <div style={{ flex: 1 }}>
                                    <div style={{ fontSize: "0.75rem", fontWeight: 700, color: layer.color, letterSpacing: "0.05em" }}>
                                        {layer.label}
                                    </div>
                                    <div style={{ fontSize: "0.7rem", color: "#8b949e", marginTop: "0.15rem" }}>
                                        {layer.sublabel}
                                    </div>
                                </div>
                                <div style={{
                                    fontSize: "0.65rem", color: layer.color, opacity: 0.6,
                                    transform: active === layer.id ? "rotate(90deg)" : "rotate(0deg)",
                                    transition: "transform 0.2s",
                                }}>▶</div>
                            </div>

                            {/* Expanded code panel */}
                            {active === layer.id && (
                                <div style={{
                                    background: layer.bg,
                                    border: `1px solid ${layer.color}44`,
                                    borderTop: "none",
                                    borderRadius: "0 0 6px 6px",
                                    padding: "1.25rem",
                                    animation: "fadeIn 0.2s ease",
                                }}>
                                    <p style={{ fontSize: "0.78rem", color: "#c9d1d9", marginBottom: "1rem", lineHeight: 1.6 }}>
                                        {layer.description}
                                    </p>
                                    <pre style={{
                                        background: "rgba(0,0,0,0.4)",
                                        border: "1px solid rgba(255,255,255,0.06)",
                                        borderRadius: "4px",
                                        padding: "1rem",
                                        fontSize: "0.7rem",
                                        lineHeight: 1.7,
                                        overflowX: "auto",
                                        color: "#e6edf3",
                                        margin: 0,
                                    }}>
                                        <code>{layer.code}</code>
                                    </pre>
                                </div>
                            )}

                            {/* Connector arrow */}
                            {i < layers.length - 1 && (
                                <div style={{
                                    display: "flex", alignItems: "center", justifyContent: "center",
                                    padding: "0.15rem 0", gap: "0.5rem",
                                }}>
                                    <div style={{ width: 1, height: 20, background: "rgba(255,255,255,0.1)" }} />
                                    <span style={{ fontSize: "0.6rem", color: "#444d56", letterSpacing: "0.1em" }}>
                                        {flow[i]?.label}
                                    </span>
                                </div>
                            )}
                        </div>
                    ))}
                </div>

                {/* Summary table */}
                <div style={{
                    background: "rgba(255,255,255,0.02)",
                    border: "1px solid rgba(255,255,255,0.07)",
                    borderRadius: "6px",
                    padding: "1.25rem",
                }}>
                    <div style={{ fontSize: "0.65rem", letterSpacing: "0.2em", color: "#8b949e", marginBottom: "1rem" }}>
                        RESUMEN DE RESPONSABILIDADES
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem" }}>
                        {[
                            { label: "SageMath", role: "Exactitud algebraica", detail: "2-Selmer descent · Ш · BSD ratio", color: "#ffd54f" },
                            { label: "C++ GMP", role: "Velocidad aritmética", detail: "#E(Fₚ) · SEA algorithm · Euler product", color: "#ef9a9a" },
                            { label: "HTCondor", role: "Escala horizontal", detail: "Paralelismo por curva · RAM distribuida", color: "#00ffc8" },
                        ].map((item) => (
                            <div key={item.label} style={{
                                background: "rgba(0,0,0,0.2)",
                                borderRadius: "4px",
                                padding: "0.75rem",
                                borderTop: `2px solid ${item.color}`,
                            }}>
                                <div style={{ fontSize: "0.75rem", fontWeight: 700, color: item.color }}>{item.label}</div>
                                <div style={{ fontSize: "0.7rem", color: "#c9d1d9", marginTop: "0.25rem" }}>{item.role}</div>
                                <div style={{ fontSize: "0.65rem", color: "#8b949e", marginTop: "0.25rem", lineHeight: 1.5 }}>{item.detail}</div>
                            </div>
                        ))}
                    </div>
                </div>

                <div style={{ marginTop: "1.5rem", fontSize: "0.65rem", color: "#444d56", textAlign: "center", letterSpacing: "0.1em" }}>
                    C++ NO REEMPLAZA SAGEMATH — LE DELEGA SOLO LAS OPERACIONES ARITMÉTICAS COSTOSAS
                </div>
            </div>

            <style>{`
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
      `}</style>
        </div>
    );
}
