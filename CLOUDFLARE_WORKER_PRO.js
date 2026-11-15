/**
 * AutoReel Cloudflare Worker — Webhook Oficial para @Maykel0007_bot
 * Interfaz Profesional Completa: Menús, Previews, Dashboard, Ajustes Interactivos y Dispatch a GitHub
 */

const GITHUB_REPO = "miguelcalderonnuevo123-star/Auto_reel";
// Blindaje de Seguridad: Los tokens se cargan dinámicamente desde Cloudflare Secrets (Variables de Entorno)
let GITHUB_TOKEN = "";
let TELEGRAM_TOKEN = "";

function setupEnv(env) {
  if (env && env.GITHUB_TOKEN) GITHUB_TOKEN = env.GITHUB_TOKEN;
  else if (typeof GITHUB_TOKEN_SECRET !== "undefined") GITHUB_TOKEN = GITHUB_TOKEN_SECRET;

  if (env && env.TELEGRAM_TOKEN) TELEGRAM_TOKEN = env.TELEGRAM_TOKEN;
  else if (typeof TELEGRAM_TOKEN_SECRET !== "undefined") TELEGRAM_TOKEN = TELEGRAM_TOKEN_SECRET;
}

// Cuentas de la Granja y sus datos configurados (10 Cuentas)
const CUENTAS = {
  frutnovelas776: {
    nombre: "@frutnovelas776",
    icono: "🍓",
    device: "Samsung Galaxy A52",
    tipo: "Manual",
    cta: "SÍGUEME PARA DESCUBRIR|LA PRÓXIMA HISTORIA",
    hashtags: "#frutinovelas #fruit #foodstory #partii #capibara",
    comentario: "Activo (Dinámico + Pin)"
  },
  novelas_frutosass: {
    nombre: "@novelas_frutosass",
    icono: "🍍",
    device: "Redmi Note 11",
    tipo: "Manual",
    cta: "SÍGUEME PARA DESCUBRIR|LA PRÓXIMA HISTORIA",
    hashtags: "#frutinovelas #fruit #foodstory #partii #capibara",
    comentario: "Activo (Dinámico + Pin)"
  },
  frutnovelas777: {
    nombre: "@frutnovelas777",
    icono: "🍉",
    device: "Moto G84 5G",
    tipo: "Manual",
    cta: "SÍGUEME PARA DESCUBRIR|LA PRÓXIMA HISTORIA",
    hashtags: "#frutinovelas #fruit #foodstory #partii #capibara",
    comentario: "Activo (Dinámico + Pin)"
  },
  novel_asanimadas: {
    nombre: "@novel_asanimadas",
    icono: "🍇",
    device: "Google Pixel 7",
    tipo: "Manual (Control Total)",
    cta: "SÍGUEME PARA DESCUBRIR|LA PRÓXIMA HISTORIA",
    hashtags: "#frutinovelas #fruit #foodstory #partii #capibara",
    comentario: "Activo (Dinámico + Pin)"
  },
  bibliareflexiones_a: {
    nombre: "@bibliareflexiones.a",
    icono: "📖",
    device: "Galaxy S23",
    tipo: "Manual",
    cta: "SÍGUEME PARA MÁS REFLEXIONES|Y PALABRA DE DIOS CADA DÍA",
    hashtags: "#biblia #reflexiones #fe #dios #historiasbiblicas #esperanza #paratii",
    comentario: "Activo (Dinámico + Pin)"
  },
  historias_frutales_hd: {
    nombre: "@historias_frutales_hd",
    icono: "🍒",
    device: "OnePlus 11",
    tipo: "Manual",
    cta: "SÍGUEME PARA DESCUBRIR|LA PRÓXIMA HISTORIA",
    hashtags: "#frutinovelas #historias #cuentos #frutas #capibara",
    comentario: "Activo (Dinámico + Pin)"
  },
  fruticuentos_oficial: {
    nombre: "@fruticuentos_oficial",
    icono: "🫐",
    device: "Galaxy S22",
    tipo: "Manual",
    cta: "SÍGUEME PARA DESCUBRIR|LA PRÓXIMA HISTORIA",
    hashtags: "#frutinovelas #cuentos #historias #viral #partii",
    comentario: "Activo (Dinámico + Pin)"
  },
  novelas_frutas_pro: {
    nombre: "@novelas_frutas_pro",
    icono: "🍊",
    device: "Xiaomi 13",
    tipo: "Manual",
    cta: "SÍGUEME PARA DESCUBRIR|LA PRÓXIMA HISTORIA",
    hashtags: "#frutinovelas #frutas #historiasanimadas #drama #parati",
    comentario: "Activo (Dinámico + Pin)"
  },
  frutidramas_top: {
    nombre: "@frutidramas_top",
    icono: "🍋",
    device: "Motorola Edge 40",
    tipo: "Manual",
    cta: "SÍGUEME PARA DESCUBRIR|LA PRÓXIMA HISTORIA",
    hashtags: "#frutinovelas #dramas #historias #humor #reels",
    comentario: "Activo (Dinámico + Pin)"
  },
  reino_frutosas: {
    nombre: "@reino_frutosas",
    icono: "🥭",
    device: "Sony Xperia 1 V",
    tipo: "Manual",
    cta: "SÍGUEME PARA DESCUBRIR|LA PRÓXIMA HISTORIA",
    hashtags: "#frutinovelas #reino #frutosas #historia #viral",
    comentario: "Activo (Dinámico + Pin)"
  }
};

// Sesiones en memoria para el Asistente Interactivo de Login
const LOGIN_SESSIONS = new Map();
const TWO_FACTOR_CODES = new Map();

export default {
  async fetch(request, env, ctx) {
    setupEnv(env);
    const url = new URL(request.url);

    if (request.method === "GET") {
      // Endpoint para que login_telegram.py en GitHub Actions consulte códigos 2FA
      if (url.pathname === "/2fa") {
        const acc = (url.searchParams.get("account") || "").toLowerCase().replace("@", "");
        const item = (acc && TWO_FACTOR_CODES.get(acc)) || TWO_FACTOR_CODES.get("default");
        if (item && (Date.now() - item.ts < 300000)) { // 5 minutos de validez
          return new Response(JSON.stringify({ ok: true, code: item.code }), {
            status: 200,
            headers: { "Content-Type": "application/json" }
          });
        }
        return new Response(JSON.stringify({ ok: false, message: "No 2FA code yet" }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        });
      }

      return new Response("✅ AutoReel Cloudflare Worker Activo y Operativo 24/7 (10 Cuentas)", { status: 200 });
    }

    try {
      const update = await request.json();
      await handleTelegramUpdate(update);
      return new Response("OK", { status: 200 });
    } catch (err) {
      console.error("Worker error:", err);
      return new Response("OK", { status: 200 });
    }
  },

  async scheduled(event, env, ctx) {
    setupEnv(env);
    // Cron inteligente: Evalúa el planificador 100% gratis en Cloudflare sin consumir minutos de GitHub Actions
    if (ctx && ctx.waitUntil) {
      ctx.waitUntil(handleSmartCron(env));
    } else {
      await handleSmartCron(env);
    }
  }
};

async function handleSmartCron(env) {
  try {
    const ahora = new Date();
    const utc = ahora.getTime() + (ahora.getTimezoneOffset() * 60000);
    const horaPeru = new Date(utc + (3600000 * -5));
    const hora = horaPeru.getHours();

    // Ventana permitida: 9:00 a 22:00 hora Perú/Colombia (UTC-5)
    if (hora < 9 || hora >= 22) {
      console.log(`Cron inteligente: hora ${hora}:00 está fuera de la ventana (9-22 UTC-5). Omitiendo.`);
      return;
    }

    const granja = await ghApi("contents/cuentas_granja.json", "application/vnd.github.raw+json", true);
    if (!granja || !granja.auto_diario || !granja.auto_diario.activo) {
      console.log("Cron inteligente: Piloto automático global inactivo.");
      return;
    }

    const cuentasActivas = Object.entries(granja.cuentas || {}).filter(([id, c]) => c.activa && c.auto_diario);
    if (cuentasActivas.length === 0) {
      console.log("Cron inteligente: Ninguna cuenta tiene auto_diario activo hoy. ¡0 minutos gastados en GitHub!");
      return;
    }

    console.log(`Cron inteligente: Disparando GitHub Actions para publicación (${cuentasActivas.length} cuentas activas)...`);
    await triggerGitHubDispatch({ action_mode: "cron_auto" }, "cron_auto");
  } catch (err) {
    console.error("Error en handleSmartCron:", err);
  }
}

async function handleTelegramUpdate(update) {
  // 1) Si presionó un botón interactivo (Callback Query)
  if (update.callback_query) {
    await handleCallbackQuery(update.callback_query);
    return;
  }

  // 2) Si envió un mensaje de texto
  const msg = update.message;
  if (!msg || !msg.text) return;

  const chatId = msg.chat.id;
  const chatKey = String(chatId);
  const text = msg.text.trim();

  // Cancelar cualquier flujo interactivo activo
  if (text === "/cancelar" || text === "❌ Cancelar" || text.toLowerCase() === "cancelar") {
    LOGIN_SESSIONS.delete(chatKey);
    await sendTelegram(chatId, "❌ Operación cancelada.");
    await sendMainMenu(chatId);
    return;
  }

  // Si el usuario envió un código 2FA numérico de 6 dígitos
  if (/^\d{6}$/.test(text)) {
    TWO_FACTOR_CODES.set("default", { code: text, ts: Date.now() });
    for (const acc of Object.keys(CUENTAS)) {
      TWO_FACTOR_CODES.set(acc, { code: text, ts: Date.now() });
    }
    const current = LOGIN_SESSIONS.get(chatKey);
    if (current && current.account) {
      TWO_FACTOR_CODES.set(current.account, { code: text, ts: Date.now() });
    }
    await deleteTelegramMessage(chatId, msg.message_id);
    await sendTelegram(chatId, `⚡ <b>Código 2FA recibido:</b> <code>${text}</code>\nValidando con Instagram en la nube...`);
    return;
  }

  // Comprobar si el usuario está en el Asistente Interactivo de Login
  let loginState = LOGIN_SESSIONS.get(chatKey);
  if (!loginState && msg.reply_to_message && msg.reply_to_message.text) {
    const repText = msg.reply_to_message.text;
    const match = repText.match(/\[LOGIN:([^:]+):([^:]+)(?::([^\]]+))?\]/);
    if (match) {
      loginState = {
        account: match[1],
        step: match[2],
        username: match[3] || match[1],
        ts: Date.now()
      };
    }
  }

  if (loginState && (Date.now() - (loginState.ts || 0) < 15 * 60 * 1000)) {
    if (loginState.step === "awaiting_password") {
      // Borrar la contraseña del chat inmediatamente por privacidad
      await deleteTelegramMessage(chatId, msg.message_id);

      const accountId = loginState.account;
      const username = loginState.username || accountId;
      const password = text;

      LOGIN_SESSIONS.delete(chatKey);

      const c = CUENTAS[accountId] || { nombre: "@" + accountId };
      await sendTelegram(chatId, 
`╔════════════════════════════════╗
   ⏳ CONECTANDO A INSTAGRAM...
╚════════════════════════════════╝
👤 <b>Cuenta:</b> ${c.nombre} (<code>${username}</code>)
🔒 <b>Contraseña:</b> Recibida y borrada del chat de forma segura
🌐 <b>Servidor:</b> Levantando Chromium en la nube (GitHub Actions)...

<i>📲 Si Instagram envía un código 2FA o SMS de verificación, te lo pediré aquí mismo en unos segundos.</i>`
      );

      await triggerGitHubDispatch({
        login_account: accountId,
        login_username: username,
        login_password: password,
        chat_id: String(chatId)
      }, "telegram_login");
      return;
    }

    if (loginState.step === "awaiting_username") {
      const accountId = loginState.account;
      const newUsername = text.replace("@", "").trim();

      LOGIN_SESSIONS.set(chatKey, {
        step: "awaiting_password",
        account: accountId,
        username: newUsername,
        ts: Date.now()
      });

      const c = CUENTAS[accountId] || { nombre: "@" + accountId };
      const promptPwd = 
`╔════════════════════════════════╗
   🔑 INGRESO DE CONTRASEÑA
╚════════════════════════════════╝
📱 <b>Cuenta granja:</b> ${c.nombre}
👤 <b>Usuario configurado:</b> <code>${newUsername}</code>

✍️ <b>Ahora escribe la contraseña de Instagram aquí abajo en el chat:</b>

🛡️ <b>Protección Total de Privacidad:</b>
• Tu mensaje con la clave se <b>BORRARÁ AL INSTANTE</b> del chat apenas lo envíes.
• Si tu cuenta pide código 2FA / SMS, te lo pediré por aquí.

<i>[LOGIN:${accountId}:awaiting_password:${newUsername}]</i>`;

      await sendTelegram(chatId, promptPwd, null, [
        [{ text: "❌ Cancelar", callback_data: "login_cancel" }]
      ]);
      return;
    }

    if (loginState.step === "awaiting_sessionid") {
      await deleteTelegramMessage(chatId, msg.message_id);

      const accountId = loginState.account;
      const sessionId = text;
      LOGIN_SESSIONS.delete(chatKey);

      const c = CUENTAS[accountId] || { nombre: "@" + accountId };
      await sendTelegram(chatId, 
`╔════════════════════════════════╗
   ⏳ GUARDANDO SESIÓN DIRECTA
╚════════════════════════════════╝
👤 <b>Cuenta:</b> ${c.nombre}
🍪 <b>Cookie:</b> Recibida y borrada del chat
🔒 <b>Guardando en GitHub Secrets...</b>`
      );

      await triggerGitHubDispatch({
        login_account: accountId,
        login_sessionid: sessionId,
        chat_id: String(chatId)
      }, "telegram_login");
      return;
    }
  }

  // Comandos de navegación
  if (text === "/start" || text === "🎬 Subir Reel Rápido") {
    await sendMainMenu(chatId);
    return;
  }

  if (text === "/estado" || text === "📊 Estado de la Granja") {
    await sendStatusDashboard(chatId);
    return;
  }

  // Métricas profundas y ranking de la granja
  if (text === "/stats" || text === "/estadisticas" || text === "/metricas" || text === "/ranking" || text === "📈 Estadísticas" || text === "📈 Estadísticas Detalladas") {
    await sendStatsDashboard(chatId);
    return;
  }

  if (text === "/config" || text === "⚙️ Ajustes de Cuentas" || text === "⚙️ Configurar Cuentas") {
    await sendConfigMenu(chatId);
    return;
  }

  if (text === "/cuentas" || text === "📲 Cuentas") {
    await sendAccountsList(chatId);
    return;
  }

  if (text === "/conectar" || text === "/login" || text === "🔑 Conectar Cuenta") {
    await sendConnectMenu(chatId);
    return;
  }

  if (text.startsWith("/gemini ") || text.startsWith("/ia ")) {
    await handleGeminiCommand(chatId, text, msg.message_id);
    return;
  }

  if (text === "/gemini" || text === "/ia") {
    await sendGeminiInfo(chatId);
    return;
  }

  if (text.startsWith("/clave ") || text.startsWith("/conectar ") || text.startsWith("/login ")) {
    await handleLoginCommand(chatId, text, msg.message_id);
    return;
  }

  if (text.startsWith("/sesion ")) {
    await handleSessionCommand(chatId, text, msg.message_id);
    return;
  }

  // Si pegó un enlace de TikTok
  if (text.includes("tiktok.com")) {
    await handleTikTokLink(chatId, text);
    return;
  }

  // Si escribió cualquier otra cosa, responder con ayuda
  await sendTelegram(chatId, "👋 Envíame un enlace de TikTok para transformarlo en Reel 1080x1920, o usa el menú de abajo:", {
    keyboard: [
      [{ text: "🎬 Subir Reel Rápido" }, { text: "📊 Estado de la Granja" }],
      [{ text: "⚙️ Ajustes de Cuentas" }, { text: "📈 Estadísticas" }],
      [{ text: "📲 Cuentas" }, { text: "🔑 Conectar Cuenta" }]
    ],
    resize_keyboard: true
  });
}

async function sendMainMenu(chatId) {
  const panel = 
`╔════════════════════════════════╗
   🎬 AUTOREEL CLOUD STUDIO 24/7
╚════════════════════════════════╝
⚡ <b>Sistema Serverless Activo</b>
📱 10 cuentas configuradas (Android virtual)
☁️ Servidor: GitHub Actions (May777p)
📲 Auto-Stories: Activo en cada publicación

<b>¿Cómo usarlo?</b>
• <b>Pega cualquier enlace de TikTok</b> directamente aquí para subirlo a Instagram.
• O usa los botones inferiores para supervisar la granja:`;

  await sendTelegram(chatId, panel, {
    keyboard: [
      [{ text: "🎬 Subir Reel Rápido" }, { text: "📊 Estado de la Granja" }],
      [{ text: "⚙️ Ajustes de Cuentas" }, { text: "📈 Estadísticas" }],
      [{ text: "📲 Cuentas" }, { text: "🔑 Conectar Cuenta" }]
    ],
    resize_keyboard: true
  });
}

// Mejora #1: Caché en memoria para evitar Rate Limits de GitHub API y responder en milisegundos (TTL 2 minutos)
const GITHUB_CACHE = new Map();
const CACHE_TTL_MS = 120 * 1000;

async function ghApi(path, accept = "application/vnd.github.raw+json", forceFresh = false) {
  const cacheKey = `${path}::${accept}`;
  const now = Date.now();
  if (!forceFresh && GITHUB_CACHE.has(cacheKey)) {
    const entry = GITHUB_CACHE.get(cacheKey);
    if (now - entry.ts < CACHE_TTL_MS) {
      return entry.data;
    }
  }

  const r = await fetch(`https://api.github.com/repos/${GITHUB_REPO}/${path}`, {
    headers: {
      "Authorization": `token ${GITHUB_TOKEN}`,
      "Accept": accept,
      "User-Agent": "AutoReel-Cloudflare-Worker"
    }
  });
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);

  let parsed;
  if (accept.includes("json")) {
    parsed = await r.json();
  } else {
    parsed = await r.text();
  }

  GITHUB_CACHE.set(cacheKey, { ts: now, data: parsed });
  return parsed;
}

function hace(ms) {
  if (!ms || ms < 0) return "—";
  const m = Math.floor(ms / 60000);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  if (h < 48) return `${h} h ${m % 60} min`;
  return `${Math.floor(h / 24)} d`;
}

async function sendStatusDashboard(chatId, messageId = null, forceFresh = false) {
  const ZONA = -5; // hora local (Perú/Colombia)
  try {
    const [hist, granja, colaTxt, runs] = await Promise.all([
      ghApi("contents/historial_bot.json", "application/vnd.github.raw+json", forceFresh),
      ghApi("contents/cuentas_granja.json", "application/vnd.github.raw+json", forceFresh),
      ghApi("contents/cola_videos.txt", "application/vnd.github.raw", forceFresh),
      ghApi("actions/runs?per_page=1", "application/vnd.github+json", forceFresh)
    ]);

    const ahora = Date.now();
    const diaLocal = (ts) => new Date(ts + ZONA * 3600000).toISOString().slice(0, 10);
    const hoy = diaLocal(ahora);
    const entradas = (hist.history || []).map((h) => ({
      ts: Date.parse(String(h.date || "").replace(" ", "T") + "Z"),
      cuentas: h.accounts || [],
      ok: !!String(h.ig_link || "").trim()
    })).filter((h) => !isNaN(h.ts) && h.ok);

    const auto = granja.auto_diario || {};
    const filas = [];
    let totalHoy = 0;
    for (const [cid, c] of Object.entries(granja.cuentas || {})) {
      const mias = entradas.filter((h) => h.cuentas.includes(cid));
      const nHoy = mias.filter((h) => diaLocal(h.ts) === hoy).length;
      const n24 = mias.filter((h) => ahora - h.ts <= 86400000).length;
      totalHoy += nHoy;
      let ultima = mias.length ? Math.max(...mias.map((h) => h.ts)) : 0;
      const lu = (hist.last_upload_by_account || {})[cid];
      if (lu && lu * 1000 > ultima) ultima = lu * 1000;
      const pausa = (hist.pausa_cuentas || {})[cid];
      const pausada = pausa && pausa * 1000 > ahora;
      const icono = (CUENTAS[cid] && CUENTAS[cid].icono) || "📱";
      let modo = "Inactiva";
      if (c.activa) {
        modo = c.auto_diario === false ? "Manual" : `Auto ${c.posts_por_dia || auto.posts_por_dia || 2}/día`;
      }
      filas.push(
        `${icono} <b>@${cid}</b> | ${modo}${pausada ? " | ⏸️ PAUSADA " + hace(pausa * 1000 - ahora) : ""}\n` +
        `     hoy: ${nHoy} · 24 h: ${n24} · última: ${ultima ? "hace " + hace(ahora - ultima) : "—"}`
      );
    }

    const cola = colaTxt.split("\n").filter((l) => l.trim() && !l.trim().startsWith("#") && l.includes("tiktok.com")).length;
    const run = (runs.workflow_runs || [])[0];
    const estadoRun = run
      ? `#${run.run_number} ${run.status === "completed" ? (run.conclusion === "success" ? "✅" : "❌ " + run.conclusion) : "⏳ " + run.status} (${run.event}) hace ${hace(ahora - Date.parse(run.created_at))}`
      : "—";

    const dashboard =
`╔════════════════════════════════╗
      📊 ESTADO DE LA GRANJA
╚════════════════════════════════╝
${filas.join("\n")}

━━━━━━━━━━━━━━━━━━━━━━━━━━
🎬 <b>Reels publicados hoy:</b> ${totalHoy}
📥 <b>Cola de videos:</b> ${cola}
🗂️ <b>Videos ya procesados:</b> ${(hist.processed_ids || []).length}
⚙️ <b>Última ejecución:</b> ${estadoRun}
🤖 <b>Piloto automático:</b> ${auto.activo === false ? "apagado" : "encendido"} (ventana ${(auto.ventana || [9, 22]).join("–")} h)`;

    const pausadas = Object.keys(hist.pausa_cuentas || {}).filter((cid) => (hist.pausa_cuentas[cid] * 1000) > ahora);
    const botones = [];
    if (pausadas.length > 0) {
      botones.push([
        { text: `🔑 Reconectar @${pausadas[0]}`, callback_data: `login_acc:${pausadas[0]}` }
      ]);
    }
    botones.push(
      [
        { text: "🔄 Actualizar Estado", callback_data: "refresh_status" },
        { text: "📈 Estadísticas", callback_data: "view_stats" }
      ],
      [
        { text: "⚙️ Configurar Cuentas", callback_data: "open_config" },
        { text: "🔙 Menú Principal", callback_data: "main_menu" }
      ]
    );

    if (messageId) {
      await editTelegram(chatId, messageId, dashboard, botones);
    } else {
      await sendTelegram(chatId, dashboard, null, botones);
    }
  } catch (err) {
    console.error("Error en /estado:", err);
    await sendTelegram(chatId, `⚠️ No pude leer el estado desde GitHub: ${String(err.message || err).slice(0, 120)}`);
  }
}

// Mejora #8: Dashboard detallado de estadísticas de rendimiento y deduplicación
async function sendStatsDashboard(chatId, messageId = null, forceFresh = false) {
  const ZONA = -5;
  try {
    const [hist, granja, colaTxt, runs] = await Promise.all([
      ghApi("contents/historial_bot.json", "application/vnd.github.raw+json", forceFresh),
      ghApi("contents/cuentas_granja.json", "application/vnd.github.raw+json", forceFresh),
      ghApi("contents/cola_videos.txt", "application/vnd.github.raw", forceFresh),
      ghApi("actions/runs?per_page=10", "application/vnd.github+json", forceFresh)
    ]);

    const ahora = Date.now();
    const entradas = (hist.history || []).map((h) => ({
      ts: Date.parse(String(h.date || "").replace(" ", "T") + "Z"),
      cuentas: h.accounts || [],
      ok: !!String(h.ig_link || "").trim()
    })).filter((h) => !isNaN(h.ts) && h.ok);

    const totalProcesados = (hist.processed_ids || []).length;
    const totalExitosos = entradas.length;
    const totalHuellas = (hist.huellas_videos || []).length;
    const duplicadosBloqueados = hist.duplicates_blocked || 0;

    const hace7Dias = ahora - 7 * 86400000;
    const ultimos7 = entradas.filter((h) => h.ts >= hace7Dias).length;
    const promDiario = (ultimos7 / 7).toFixed(1);

    const lineasCuentas = [];
    for (const [cid, c] of Object.entries(granja.cuentas || {})) {
      const mias = entradas.filter((h) => h.cuentas.includes(cid));
      const mias7 = mias.filter((h) => h.ts >= hace7Dias).length;
      const icono = (CUENTAS[cid] && CUENTAS[cid].icono) || "📱";
      lineasCuentas.push(`  ${icono} <b>@${cid}:</b> ${mias.length} total (${mias7} en 7d)`);
    }

    const listaRuns = runs.workflow_runs || [];
    const completados = listaRuns.filter((r) => r.status === "completed");
    const exitosos = completados.filter((r) => r.conclusion === "success").length;
    const pctExito = completados.length ? Math.round((exitosos / completados.length) * 100) : 100;

    const stats =
`╔════════════════════════════════╗
      📈 ESTADÍSTICAS DETALLADAS
╚════════════════════════════════╝
🗂️ <b>Videos procesados:</b> ${totalProcesados}
🎬 <b>Reels publicados con éxito:</b> ${totalExitosos}
♻️ <b>Duplicados prevenidos:</b> ${duplicadosBloqueados} (sin costo)
🏷️ <b>Huellas de deduplicación:</b> ${totalHuellas}

📊 <b>Rendimiento por Cuenta:</b>
${lineasCuentas.join("\n")}

⚡ <b>Métricas del Sistema:</b>
• <b>Frecuencia:</b> ~${promDiario} reels/día (últimos 7 días)
• <b>Tasa de éxito de workflows:</b> ${pctExito}% (${exitosos}/${completados.length})
• <b>Modo de Render:</b> 1080x1920 HD Eco-Bitrate (3.5 Mbps)
• <b>Portadas dinámicas:</b> Rotación de 4 estilos (Gold, Cyan, Crimson, Emerald)
• <b>Caché API:</b> TTL 2 min activo (sin rate-limits)`;

    const botones = [
      [
        { text: "🔄 Actualizar Stats", callback_data: "refresh_stats" },
        { text: "📊 Ver Estado en Vivo", callback_data: "refresh_status" }
      ],
      [
        { text: "⚙️ Configurar Cuentas", callback_data: "open_config" },
        { text: "🔙 Menú Principal", callback_data: "main_menu" }
      ]
    ];

    if (messageId) {
      await editTelegram(chatId, messageId, stats, botones);
    } else {
      await sendTelegram(chatId, stats, null, botones);
    }
  } catch (err) {
    console.error("Error en /stats:", err);
    await sendTelegram(chatId, `⚠️ No pude leer las estadísticas: ${String(err.message || err).slice(0, 120)}`);
  }
}

async function sendConfigMenu(chatId, messageId = null) {
  const texto = 
`╔════════════════════════════════╗
   ⚙️ CONFIGURACIÓN DE CUENTAS
╚════════════════════════════════╝
Selecciona la cuenta que deseas inspeccionar o configurar:`;

  const inlineKeyboard = [];
  const entries = Object.entries(CUENTAS);
  for (let i = 0; i < entries.length; i += 2) {
    const row = [];
    const [id1, c1] = entries[i];
    row.push({ text: `${c1.icono} ${c1.nombre}`, callback_data: `cfg_acc:${id1}` });
    if (i + 1 < entries.length) {
      const [id2, c2] = entries[i + 1];
      row.push({ text: `${c2.icono} ${c2.nombre}`, callback_data: `cfg_acc:${id2}` });
    }
    inlineKeyboard.push(row);
  }
  inlineKeyboard.push([
    { text: "📊 Ver Estado de la Granja", callback_data: "refresh_status" },
    { text: "🔙 Menú Principal", callback_data: "main_menu" }
  ]);

  if (messageId) {
    await editTelegram(chatId, messageId, texto, inlineKeyboard);
  } else {
    await sendTelegram(chatId, texto, null, inlineKeyboard);
  }
}

async function sendAccountDetail(chatId, messageId, accountId) {
  const c = CUENTAS[accountId];
  if (!c) return;

  const detalle = 
`╔════════════════════════════════╗
   ${c.icono} AJUSTES DE ${c.nombre.toUpperCase()}
╚════════════════════════════════╝
📱 <b>Dispositivo Virtual:</b> ${c.device}
🕹️ <b>Modo de Trabajo:</b> ${c.tipo}
${c.fuente ? `🔗 <b>Fuente TikTok:</b> ${c.fuente}\n` : ""}
🟡 <b>Texto CTA (Abajo):</b>
<code>${c.cta}</code>

#️⃣ <b>Hashtags por defecto:</b>
<code>${c.hashtags}</code>

💬 <b>Auto-Comentario:</b> ${c.comentario}`;

  const botones = [
    [
      { text: "🔑 Conectar / Renovar Sesión", callback_data: `login_acc:${accountId}` }
    ],
    [
      { text: "⚡ Probar Subida Ahora", callback_data: `test_auto:${accountId}` }
    ],
    [
      { text: "🔙 Volver a Cuentas", callback_data: "open_config" }
    ]
  ];

  await editTelegram(chatId, messageId, detalle, botones);
}

async function sendConnectMenu(chatId, messageId = null) {
  const panel = 
`╔════════════════════════════════╗
   🔑 CONECTAR CUENTA DESDE EL MÓVIL
╚════════════════════════════════╝
Inicia sesión directamente desde Telegram sin tocar la computadora.

👇 <b>Selecciona la cuenta que deseas conectar o renovar:</b>`;

  const inlineKeyboard = [];
  const entries = Object.entries(CUENTAS);
  for (let i = 0; i < entries.length; i += 2) {
    const row = [];
    const [id1, c1] = entries[i];
    row.push({ text: `${c1.icono} ${c1.nombre}`, callback_data: `login_acc:${id1}` });
    if (i + 1 < entries.length) {
      const [id2, c2] = entries[i + 1];
      row.push({ text: `${c2.icono} ${c2.nombre}`, callback_data: `login_acc:${id2}` });
    }
    inlineKeyboard.push(row);
  }
  inlineKeyboard.push([{ text: "🤖 Configurar Gemini IA", callback_data: "gemini_info" }]);
  inlineKeyboard.push([{ text: "❌ Cancelar", callback_data: "cancelar" }]);

  if (messageId) {
    await editTelegram(chatId, messageId, panel, inlineKeyboard);
  } else {
    await sendTelegram(chatId, panel, null, inlineKeyboard);
  }
}

async function sendInteractiveLoginCard(chatId, messageId, accountId) {
  const c = CUENTAS[accountId] || { nombre: "@" + accountId, icono: "📱", device: "Android Virtual" };
  const texto = 
`╔════════════════════════════════╗
   🔐 CONEXIÓN INSTAGRAM (LOGIN)
╚════════════════════════════════╝
📱 <b>Cuenta de la Granja:</b> ${c.icono} ${c.nombre}
👤 <b>Usuario predeterminado:</b> <code>${accountId}</code>
📶 <b>Dispositivo Android:</b> ${c.device}

👇 <b>Selecciona cómo deseas conectar:</b>
• <b>Ingresar Contraseña:</b> Escribe tu clave en el chat y se borrará sola al instante.
• <b>Cambiar Usuario:</b> Si usas otro usuario, teléfono o correo en Instagram.
• <b>Pegar Cookie:</b> Conexión directa mediante sessionid.`;

  const inlineKeyboard = [
    [
      { text: "🔑 Ingresar Contraseña", callback_data: `login_btn:pwd:${accountId}` }
    ],
    [
      { text: "👤 Cambiar Usuario", callback_data: `login_btn:usr:${accountId}` },
      { text: "🍪 Pegar Cookie SessionID", callback_data: `login_btn:sid:${accountId}` }
    ],
    [
      { text: "🔙 Volver a Cuentas", callback_data: "open_config" }
    ]
  ];

  if (messageId) {
    await editTelegram(chatId, messageId, texto, inlineKeyboard);
  } else {
    await sendTelegram(chatId, texto, null, inlineKeyboard);
  }
}

async function handleLoginCommand(chatId, text, messageId) {
  // Eliminar el mensaje con la contraseña inmediatamente por seguridad
  await deleteTelegramMessage(chatId, messageId);

  const partes = text.trim().split(/\s+/);
  if (partes.length < 3) {
    await sendTelegram(chatId, "⚠️ <b>Formato incorrecto.</b> Debe ser:\n<code>/login 2 TU_CONTRASEÑA</code>\no\n<code>/login novelas_frutosass TU_CONTRASEÑA</code>");
    return;
  }

  const NUM_MAP = {
    "1": "frutnovelas776", "2": "novelas_frutosass", "3": "frutnovelas777", "4": "novel_asanimadas",
    "5": "bibliareflexiones_a", "6": "historias_frutales_hd", "7": "fruticuentos_oficial",
    "8": "novelas_frutas_pro", "9": "frutidramas_top", "10": "reino_frutosas"
  };
  const rawAcc = partes[1].toLowerCase().replace("@", "");
  const accountId = NUM_MAP[rawAcc] || rawAcc;
  const password = partes.slice(2).join(" ");
  const c = CUENTAS[accountId] || { nombre: "@" + accountId };

  await sendTelegram(chatId, 
`⏳ <b>INICIANDO SESIÓN EN ${c.nombre.toUpperCase()}...</b>

🌐 Conectando emulador móvil en la nube...
🔒 Autenticando con Instagram de forma segura...
<i>Si Instagram solicita código 2FA o SMS, te avisaré aquí mismo en Telegram para que lo escribas.</i>`
  );

  await triggerGitHubDispatch({
    login_account: accountId,
    login_username: accountId,
    login_password: password,
    chat_id: String(chatId)
  }, "telegram_login");
}

async function handleSessionCommand(chatId, text, messageId) {
  // Eliminar el mensaje con la cookie inmediatamente por privacidad
  await deleteTelegramMessage(chatId, messageId);

  const partes = text.trim().split(/\s+/);
  if (partes.length < 3) {
    await sendTelegram(chatId, "⚠️ <b>Formato incorrecto.</b> Debe ser:\n<code>/sesion 2 TU_COOKIE</code>\no\n<code>/sesion novelas_frutosass TU_COOKIE</code>");
    return;
  }

  const NUM_MAP = {
    "1": "frutnovelas776", "2": "novelas_frutosass", "3": "frutnovelas777", "4": "novel_asanimadas",
    "5": "bibliareflexiones_a", "6": "historias_frutales_hd", "7": "fruticuentos_oficial",
    "8": "novelas_frutas_pro", "9": "frutidramas_top", "10": "reino_frutosas"
  };
  const rawAcc = partes[1].toLowerCase().replace("@", "");
  const accountId = NUM_MAP[rawAcc] || rawAcc;
  const sessionVal = partes.slice(2).join(" ");
  const c = CUENTAS[accountId] || { nombre: "@" + accountId };

  await sendTelegram(chatId, `⏳ <b>Guardando sesión directa para ${c.nombre}...</b>\nActualizando secretos en GitHub...`);

  await triggerGitHubDispatch({
    login_account: accountId,
    login_sessionid: sessionVal,
    chat_id: String(chatId)
  }, "telegram_login");
}

async function sendGeminiInfo(chatId) {
  const panel = 
`╔════════════════════════════════╗
   🤖 INTELIGENCIA ARTIFICIAL GEMINI
╚════════════════════════════════╝
Genera títulos y ganchos virales automáticos de máxima retención para tus Reels con <b>Google Gemini 1.5 Flash</b>.

<b>¿Cómo activarlo gratis en 1 minuto?</b>
1️⃣ Entra a: https://aistudio.google.com/app/apikey
2️⃣ Inicia sesión con tu cuenta de Google y pulsa <b>"Create API key"</b>.
3️⃣ Copia la clave que empieza por <code>GEMINI_KEY_...</code>
4️⃣ Envíamela aquí en Telegram con este formato:
<code>/gemini TU_API_KEY</code>

<i>Ejemplo:</i>
<code>/gemini GEMINI_KEY_Bxxxxxxxxxxxxxxx</code>

🔒 <i>Por seguridad, el bot borrará tu mensaje en cuanto lo reciba y guardará la clave cifrada en GitHub Secrets.</i>`;

  await sendTelegram(chatId, panel);
}

async function handleGeminiCommand(chatId, text, messageId) {
  await deleteTelegramMessage(chatId, messageId);

  const partes = text.trim().split(/\s+/);
  if (partes.length < 2) {
    await sendGeminiInfo(chatId);
    return;
  }

  const geminiKey = partes.slice(1).join("").trim();

  await sendTelegram(chatId, `⏳ <b>CONECTANDO GEMINI IA...</b>\nGuardando tu API Key cifrada en GitHub Secrets...`);

  await triggerGitHubDispatch({
    login_account: "gemini",
    gemini_key: geminiKey,
    chat_id: String(chatId)
  }, "telegram_login");
}

async function sendAccountsList(chatId) {
  const lista = 
`📲 <b>Cuentas Conectadas en la Granja:</b>

1️⃣ <b>@frutnovelas776</b> — Samsung Galaxy A52 (Manual)
2️⃣ <b>@novelas_frutosass</b> — Redmi Note 11 (Manual)
3️⃣ <b>@frutnovelas777</b> — Redmi Note 13 Pro (Manual)
4️⃣ <b>@novel_asanimadas</b> — Google Pixel 7 (Manual)
5️⃣ <b>@bibliareflexiones.a</b> — Samsung Galaxy S23 (Manual)

<i>Cada cuenta opera con dispositivo Android virtual exclusivo y huella persistente para evitar bloqueos.</i>`;

  await sendTelegram(chatId, lista);
}

async function handleTikTokLink(chatId, text) {
  const match = text.match(/https?:\/\/[^\s|]+tiktok\.com[^\s|]+/);
  if (!match) return;
  const url = match[0].trim();

  let customHook = "";
  if (text.includes("|")) {
    customHook = text.split("|").slice(1).join("|").trim().toUpperCase();
  }

  const hookDisplay = customHook 
    ? `📌 <b>Hook Personalizado:</b> ${customHook}` 
    : `📌 <b>Hook:</b> <i>(Automático del video de TikTok)</i>`;

  const tarjeta = 
`╔════════════════════════════════╗
   🎬 REEL LISTO PARA PROCESAR
╚════════════════════════════════╝
🔗 <b>Enlace:</b> ${url}
${hookDisplay}
📐 <b>Formato:</b> 1080x1920 Vertical HD
🎯 <b>Portada:</b> Frame Hunter Automático

👇 <b>¿Cómo deseas proceder?</b>
• <b>Vista Previa:</b> Te manda el video terminado aquí para revisarlo antes de subir.
• <b>Subir Directo:</b> Publica de inmediato en la cuenta seleccionada.`;

  // Nota de seguridad: Telegram limita callback_data a 64 bytes máximo.
  // Mantenemos los botones ultra-cortos ("subir:ID" o "previa:video") y leemos la URL del texto del mensaje al pulsar.
  const inlineKeyboard = [
    [
      { text: "👁️ Ver Vista Previa en Telegram (Recomendado)", callback_data: "previa:video" }
    ],
    [
      { text: "🍓 @frutnovelas776", callback_data: "subir:frutnovelas776" },
      { text: "🍍 @novelas_frutosass", callback_data: "subir:novelas_frutosass" }
    ],
    [
      { text: "🍉 @frutnovelas777", callback_data: "subir:frutnovelas777" },
      { text: "🍇 @novel_asanimadas", callback_data: "subir:novel_asanimadas" }
    ],
    [
      { text: "📖 @bibliareflexiones.a", callback_data: "subir:bibliareflexiones_a" },
      { text: "❌ Cancelar", callback_data: "cancelar" }
    ]
  ];

  await sendTelegram(chatId, tarjeta, null, inlineKeyboard);
}

async function handleCallbackQuery(cq) {
  const cqId = cq.id;
  const data = cq.data || "";
  const chatId = cq.message.chat.id;
  const msgId = cq.message.message_id;

  await answerCallback(cqId);

  if (data === "cancelar") {
    await editTelegram(chatId, msgId, "❌ Operación cancelada.");
    return;
  }

  if (data === "main_menu") {
    await editTelegram(chatId, msgId, "🎬 Menú principal listo. Pega un link de TikTok o usa los botones de abajo.");
    return;
  }

  if (data === "refresh_status") {
    await sendStatusDashboard(chatId, msgId, true);
    return;
  }

  if (data === "view_stats") {
    await sendStatsDashboard(chatId, msgId, false);
    return;
  }

  if (data === "refresh_stats") {
    await sendStatsDashboard(chatId, msgId, true);
    return;
  }

  if (data === "open_config") {
    await sendConfigMenu(chatId, msgId);
    return;
  }

  if (data === "gemini_info") {
    await sendGeminiInfo(chatId);
    return;
  }

  if (data.startsWith("cfg_acc:")) {
    const accId = data.split(":")[1];
    await sendAccountDetail(chatId, msgId, accId);
    return;
  }

  if (data === "login_cancel") {
    LOGIN_SESSIONS.delete(String(chatId));
    await editTelegram(chatId, msgId, "❌ Inicio de sesión cancelado.", [
      [{ text: "⚙️ Volver a Cuentas", callback_data: "open_config" }],
      [{ text: "🔙 Menú Principal", callback_data: "main_menu" }]
    ]);
    return;
  }

  if (data.startsWith("login_acc:")) {
    const accId = data.split(":")[1];
    await sendInteractiveLoginCard(chatId, msgId, accId);
    return;
  }

  if (data.startsWith("login_btn:pwd:")) {
    const partes = data.split(":");
    const accId = partes[2];
    const username = partes[3] || accId;

    LOGIN_SESSIONS.set(String(chatId), {
      step: "awaiting_password",
      account: accId,
      username: username,
      ts: Date.now()
    });

    const c = CUENTAS[accId] || { nombre: "@" + accId, icono: "📱" };
    const prompt = 
`╔════════════════════════════════╗
   🔑 INGRESO DE CONTRASEÑA
╚════════════════════════════════╝
📱 <b>Cuenta:</b> ${c.icono} ${c.nombre}
👤 <b>Usuario:</b> <code>${username}</code>

✍️ <b>Escribe tu contraseña de Instagram aquí abajo en el chat:</b>

🛡️ <b>Protección Total de Privacidad:</b>
• Tu mensaje con la clave se <b>BORRARÁ AL INSTANTE</b> del chat apenas lo envíes para que nadie pueda verlo.
• El bot iniciará sesión seguro en la nube con un navegador Android virtual.
• Si Instagram envía un código 2FA o SMS, te lo pediré por aquí.

<i>[LOGIN:${accId}:awaiting_password:${username}]</i>`;

    await editTelegram(chatId, msgId, prompt, [
      [{ text: "❌ Cancelar", callback_data: "login_cancel" }]
    ]);
    return;
  }

  if (data.startsWith("login_btn:usr:")) {
    const accId = data.split(":")[2];

    LOGIN_SESSIONS.set(String(chatId), {
      step: "awaiting_username",
      account: accId,
      ts: Date.now()
    });

    const c = CUENTAS[accId] || { nombre: "@" + accId, icono: "📱" };
    const prompt = 
`╔════════════════════════════════╗
   👤 CAMBIAR USUARIO DE LOGIN
╚════════════════════════════════╝
🎯 <b>Cuenta granja:</b> ${c.icono} ${c.nombre}
👤 <b>Usuario actual:</b> <code>${accId}</code>

✍️ <b>Escribe el usuario, teléfono o correo de Instagram con el que inicias sesión:</b>

<i>(Por ejemplo: ${accId} o tu_correo@gmail.com)</i>

<i>[LOGIN:${accId}:awaiting_username]</i>`;

    await editTelegram(chatId, msgId, prompt, [
      [{ text: "❌ Cancelar", callback_data: "login_cancel" }]
    ]);
    return;
  }

  if (data.startsWith("login_btn:sid:")) {
    const accId = data.split(":")[2];

    LOGIN_SESSIONS.set(String(chatId), {
      step: "awaiting_sessionid",
      account: accId,
      ts: Date.now()
    });

    const c = CUENTAS[accId] || { nombre: "@" + accId, icono: "📱" };
    const prompt = 
`╔════════════════════════════════╗
   🍪 PEGAR COOKIE SESSIONID
╚════════════════════════════════╝
📱 <b>Cuenta:</b> ${c.icono} ${c.nombre}

✍️ <b>Pega a continuación el valor de tu cookie <code>sessionid</code> de Instagram:</b>

🛡️ <i>Tu mensaje será eliminado automáticamente del chat por privacidad en cuanto lo envíes.</i>

<i>[LOGIN:${accId}:awaiting_sessionid]</i>`;

    await editTelegram(chatId, msgId, prompt, [
      [{ text: "❌ Cancelar", callback_data: "login_cancel" }]
    ]);
    return;
  }

  if (data.startsWith("test_auto:")) {
    const accId = data.split(":")[1];
    await editTelegram(chatId, msgId,
`⚡ <b>INICIANDO PRUEBA AUTOMÁTICA EN @${accId}</b>

⏳ Despertando servidor en la nube (GitHub Actions May777p)...
<i>1) Leyendo videos recientes (+30s) de la fuente</i>
<i>2) Renderizando 1080x1920 con Hook inteligente</i>
<i>3) Publicando Reel en Instagram</i>

Te avisaremos por aquí apenas finalice 🚀`
    );

    await triggerGitHubDispatch({
      target_account: accId,
      video_url: "",
      custom_hook: "",
      chat_id: String(chatId)
    });
    return;
  }

  if (data === "previa:video") {
    const msgText = cq.message ? (cq.message.text || cq.message.caption || "") : "";
    const urlMatch = msgText.match(/https?:\/\/[^\s\n]+/);
    const videoUrl = urlMatch ? urlMatch[0].trim() : "";

    let customHook = "";
    const hookMatch = msgText.match(/Hook Personalizado:\s*([^\n<]+)/);
    if (hookMatch) {
      const hVal = hookMatch[1].trim();
      if (!hVal.toLowerCase().includes("automático") && !hVal.toLowerCase().includes("automatico")) {
        customHook = hVal;
      }
    }

    await editTelegram(chatId, msgId, 
`⏳ <b>GENERANDO VISTA PREVIA CON FRAME HUNTER...</b>

🎬 <b>Video:</b> ${videoUrl}
${customHook ? `📌 <b>Hook:</b> ${customHook}\n` : ""}
<i>1) Escaneando fotogramas más expresivos</i>
<i>2) Renderizando 1080x1920 HD y portada centrada</i>
<i>3) Enviándote el video terminado por aquí para tu revisión</i>

Te llegará en unos 20-30 segundos 🚀`
    );

    await triggerGitHubDispatch({
      target_account: "frutnovelas776",
      video_url: videoUrl,
      custom_hook: customHook,
      action_mode: "preview",
      chat_id: String(chatId)
    });
    return;
  }

  if (data.startsWith("subir:")) {
    const targetAccount = data.replace("subir:", "").trim();
    
    // Extraer la URL y el Hook del mensaje original o del caption del video
    const msgText = cq.message ? (cq.message.text || cq.message.caption || "") : "";
    const urlMatch = msgText.match(/https?:\/\/[^\s\n]+/);
    const videoUrl = urlMatch ? urlMatch[0].trim() : "";
    
    let customHook = "";
    const hookMatch = msgText.match(/Hook Personalizado:\s*([^\n<]+)/);
    if (hookMatch) {
      const hVal = hookMatch[1].trim();
      if (!hVal.toLowerCase().includes("automático") && !hVal.toLowerCase().includes("automatico")) {
        customHook = hVal;
      }
    }

    const videoInfo = videoUrl ? `🎬 <b>Fuente:</b> ${videoUrl}` : `🎬 <b>Modo:</b> Procesamiento Inteligente`;

    await editTelegram(chatId, msgId, 
`⚡ <b>¡PUBLICANDO REEL EN INSTAGRAM!</b>

🎯 <b>Destino:</b> @${targetAccount}
${videoInfo}
${customHook ? `📌 <b>Hook:</b> ${customHook}\n` : ""}
⏳ <b>Procesando en la nube (GitHub Actions May777p)...</b>
<i>1) Preparando video final con portada Frame Hunter</i>
<i>2) Subiendo Reel a Instagram con huella Android real</i>
<i>3) Fijando auto-comentario para interacción</i>

Te avisaremos por aquí apenas quede publicado 🚀`
    );

    await triggerGitHubDispatch({
      target_account: targetAccount,
      video_url: videoUrl,
      custom_hook: customHook,
      action_mode: "upload",
      chat_id: String(chatId)
    });
    return;
  }
}

async function triggerGitHubDispatch(payload, eventType = "telegram_link") {
  const url = `https://api.github.com/repos/${GITHUB_REPO}/dispatches`;
  try {
    await fetch(url, {
      method: "POST",
      headers: {
        "Authorization": `token ${GITHUB_TOKEN}`,
        "Accept": "application/vnd.github+json",
        "User-Agent": "AutoReel-Cloudflare-Worker"
      },
      body: JSON.stringify({
        event_type: eventType,
        client_payload: payload
      })
    });
  } catch (e) {
    console.error("Error disparando GitHub Actions:", e);
  }
}

async function deleteTelegramMessage(chatId, messageId) {
  const url = `https://api.telegram.org/bot${TELEGRAM_TOKEN}/deleteMessage`;
  try {
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: chatId, message_id: messageId })
    });
  } catch (e) {}
}

async function sendTelegram(chatId, text, replyMarkup = null, inlineKeyboard = null) {
  const url = `https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage`;
  const body = {
    chat_id: chatId,
    text: text,
    parse_mode: "HTML",
    disable_web_page_preview: true
  };
  if (inlineKeyboard) {
    body.reply_markup = { inline_keyboard: inlineKeyboard };
  } else if (replyMarkup) {
    body.reply_markup = replyMarkup;
  }
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!res.ok) {
    const errText = await res.text();
    console.error("Telegram API Error (sendTelegram):", res.status, errText);
  }
  return res;
}

async function editTelegram(chatId, messageId, text, inlineKeyboard = null) {
  const url = `https://api.telegram.org/bot${TELEGRAM_TOKEN}/editMessageText`;
  const body = {
    chat_id: chatId,
    message_id: messageId,
    text: text,
    parse_mode: "HTML",
    disable_web_page_preview: true
  };
  if (inlineKeyboard) {
    body.reply_markup = { inline_keyboard: inlineKeyboard };
  }
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!res.ok) {
    const errText = await res.text();
    console.error("Telegram API Error (editTelegram):", res.status, errText);
  }
  return res;
}

async function answerCallback(cqId) {
  const url = `https://api.telegram.org/bot${TELEGRAM_TOKEN}/answerCallbackQuery`;
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ callback_query_id: cqId })
  });
}
