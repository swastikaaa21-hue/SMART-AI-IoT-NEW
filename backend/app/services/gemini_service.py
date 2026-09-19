"""
Google Gemini AI service with Function Calling for IoT device control.

Defines tool declarations matching the IoT domain, processes user natural-language
commands, invokes the appropriate backend functions, and returns conversational
responses.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool, content_types

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("gemini_service")

# ── Gemini Tool / Function Declarations ──────────────────────

_control_device_fn = FunctionDeclaration(
    name="control_device",
    description=(
        "Control a smart home IoT device. Use this to turn devices on/off, "
        "toggle their state, or set a specific value such as brightness."
    ),
    parameters={
        "type": "object",
        "properties": {
            "device_id": {
                "type": "string",
                "description": "The identifier of the device (e.g. 'dev-km-1' for Lampu Kamar, 'dev-km-2' for AC Kamar, or 'lampu kamar').",
            },
            "action": {
                "type": "string",
                "enum": ["turn_on", "turn_off", "toggle", "set_value"],
                "description": "The action to perform on the device.",
            },
            "value": {
                "type": "number",
                "description": "Optional numeric value for set_value actions (e.g. brightness 0-100).",
            },
        },
        "required": ["device_id", "action"],
    },
)

_get_device_status_fn = FunctionDeclaration(
    name="get_device_status",
    description="Get the current status of a specific IoT device including its state and sensor readings.",
    parameters={
        "type": "object",
        "properties": {
            "device_id": {
                "type": "string",
                "description": "The unique identifier of the device.",
            },
        },
        "required": ["device_id"],
    },
)

_list_devices_fn = FunctionDeclaration(
    name="list_devices",
    description="List all available IoT devices, optionally filtered by room or device type.",
    parameters={
        "type": "object",
        "properties": {
            "room": {
                "type": "string",
                "description": "Optional room slug to filter devices (e.g. 'living_room').",
            },
            "device_type": {
                "type": "string",
                "description": "Optional device type to filter (e.g. 'light', 'fan', 'sensor').",
            },
        },
        "required": [],
    },
)

_get_telemetry_fn = FunctionDeclaration(
    name="get_telemetry",
    description="Get recent sensor telemetry data (temperature, humidity, power) for a device.",
    parameters={
        "type": "object",
        "properties": {
            "device_id": {
                "type": "string",
                "description": "The device identifier to query telemetry for.",
            },
            "limit": {
                "type": "integer",
                "description": "Number of recent records to retrieve (default 10, max 100).",
            },
        },
        "required": ["device_id"],
    },
)

_control_room_devices_fn = FunctionDeclaration(
    name="control_room_devices",
    description=(
        "Control all devices in a specific room. For example, turn off all "
        "lights in the bedroom or turn on all devices in the living room."
    ),
    parameters={
        "type": "object",
        "properties": {
            "room": {
                "type": "string",
                "description": "Room slug identifier (e.g. 'bedroom', 'living_room').",
            },
            "action": {
                "type": "string",
                "enum": ["turn_on", "turn_off"],
                "description": "Action to apply to all devices in the room.",
            },
            "device_type": {
                "type": "string",
                "description": "Optional: only affect devices of this type (e.g. 'light').",
            },
        },
        "required": ["room", "action"],
    },
)

# Bundle all tool declarations
iot_tools = Tool(function_declarations=[
    _control_device_fn,
    _get_device_status_fn,
    _list_devices_fn,
    _get_telemetry_fn,
    _control_room_devices_fn,
])

# ── System Prompt ────────────────────────────────────────────

SYSTEM_PROMPT = """Kamu adalah Jarkvis, asisten rumah pintar yang ramah, sopan, dan profesional.

PERSONALITY & TONE:
- Gunakan bahasa Indonesia baku, formal, dan santun (menggunakan kata "Saya", "Anda", "Baik", "Terima kasih").
- Selalu memberikan pelayanan yang membantu, ramah, dan solutif.
- Singkat, jelas, dan langsung pada inti informasi (maksimal 1-2 kalimat).
- Jika pengguna berkomunikasi dalam bahasa Inggris, berikan jawaban dalam bahasa Inggris yang sopan dan profesional.

RESPONSE STYLE:
- SELALU jawab maksimal 1-2 kalimat pendek (5-15 kata).
- Jangan ulangi perintah pengguna secara berlebihan.
- Gunakan bahasa yang santun dan mudah dipahami.

DAFTAR PERANGKAT RUMAH:
- Kamar:
  * dev-km-1 (Lampu Kamar, type: light)
  * dev-km-2 (AC Kamar, type: ac)
  * dev-km-3 (Samsung TV, type: tv)
  * dev-km-4 (Smart Tirai, type: curtain)
- Ruang Tamu:
  * dev-rt-1 (Lampu Utama, type: light)
  * dev-rt-2 (Ambient Light, type: light)
  * dev-rt-3 (LG Smart TV, type: tv)
  * dev-rt-4 (Sony Soundbar, type: speaker)
- Ruang Rapat:
  * dev-rr-1 (Epson Projector, type: projector)
  * dev-rr-2 (Daikin AC Rapat, type: ac)
  * dev-rr-3 (Lampu Rapat Panel, type: light)
- Studio:
  * dev-st-1 (Sharp AC, type: ac)
  * dev-st-2 (Lampu Studio, type: light)

ATURAN WAJIB & SCANNING:
1. PERINTAH SATU RUANGAN (misal "nyalakan semua perangkat di ruang tamu", "matikan seluruh perangkat kamar"):
   * Wajib panggil `control_room_devices` dengan nama/slug ruangan (misal: room="ruang-tamu", action="turn_on").
2. PERINTAH TIDAK DETIL (misal "nyalakan ac", "matikan tv", "nyalakan lampu" tanpa menyebut nama ruangan):
   * Jika ada `[Konteks Ruangan: User sedang membuka ruangan '...']`, PRIORITASKAN perangkat di ruangan tersebut!
   * Jika TIDAK ada konteks ruangan dan ruangan belum jelas: Panggil function `list_devices` untuk SCANNING seluruh perangkat. Jika hanya ada 1 perangkat jenis itu di rumah, langsung kontrol perangkat itu. Jika ada lebih dari satu (misal AC Kamar dan AC Ruang Tamu), tanyakan kepada pengguna secara santun: "Apakah Anda ingin menyalakan AC Kamar atau AC Ruang Tamu?".
3. JANGAN PERNAH berasumsi atau mengarang konfirmasi sukses sebelum function selesai dieksekusi.
4. JIKA function mengembalikan error atau success=false, beritahukan kendala tersebut secara sopan kepada pengguna. JANGAN PERNAH menyatakan "Baik, sudah selesai!" jika perintah gagal!
5. Response maksimal 1-2 kalimat pendek yang santun dan profesional.
"""


class GeminiService:
    """
    Manages interactions with Google Gemini API including Function Calling.

    The service maintains per-session chat histories and handles the full
    function-calling loop: user message -> model response -> function execution
    -> model final answer.
    """

    def __init__(self) -> None:
        self._model: genai.GenerativeModel | None = None
        self._chat_sessions: dict[str, genai.ChatSession] = {}
        self._initialised: bool = False

    def initialise(self) -> None:
        """Configure the Gemini API client and model."""
        if not settings.GEMINI_API_KEY:
            logger.warning("gemini_api_key_not_set", msg="Gemini AI disabled")
            return

        genai.configure(api_key=settings.GEMINI_API_KEY)

        generation_config = genai.GenerationConfig(
            max_output_tokens=settings.GEMINI_MAX_TOKENS,
            temperature=settings.GEMINI_TEMPERATURE,
        )

        # List of models with automatic fallback if quota limit is hit
        self._fallback_models = [
            settings.GEMINI_MODEL or "gemini-1.5-flash",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-pro",
        ]
        # Deduplicate while preserving order
        self._fallback_models = list(dict.fromkeys(self._fallback_models))

        self._generation_config = generation_config
        self._current_model_idx = 0
        self._init_active_model()

    def _init_active_model(self) -> None:
        model_name = self._fallback_models[self._current_model_idx]
        try:
            self._model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=self._generation_config,
                tools=[iot_tools],
                system_instruction=SYSTEM_PROMPT,
            )
            self._initialised = True
            logger.info("gemini_initialised", model=model_name)
        except Exception as e:
            logger.warning("gemini_init_failed", model=model_name, error=str(e))
            if self._current_model_idx + 1 < len(self._fallback_models):
                self._current_model_idx += 1
                self._init_active_model()

    def _get_or_create_chat(self, session_id: str) -> genai.ChatSession:
        """Get or create a Gemini chat session."""
        if session_id not in self._chat_sessions:
            if not self._model:
                raise RuntimeError("Gemini model not initialised")
            self._chat_sessions[session_id] = self._model.start_chat(history=[])
        return self._chat_sessions[session_id]

    async def chat(
        self,
        message: str,
        session_id: str,
        function_executor: Any = None,
    ) -> dict[str, Any]:
        """
        Process a user message through Gemini with Function Calling support.

        Args:
            message: User's natural language input.
            session_id: Chat session identifier for conversation history.
            function_executor: Async callable that executes IoT functions.
                              Signature: async def executor(name, args) -> dict

        Returns:
            Dict containing reply text, function call info, and affected devices.
        """
        if not self._initialised or not self._model:
            return {
                "reply": "AI service is not configured. Please set GEMINI_API_KEY.",
                "function_called": None,
                "function_result": None,
                "devices_affected": [],
            }

        chat = self._get_or_create_chat(session_id)

        try:
            # Send user message to Gemini
            response = await self._send_message_async(chat, message)

            function_called: str | None = None
            function_result: dict | None = None
            devices_affected: list[str] = []

            # Check if Gemini wants to call a function
            candidate = response.candidates[0]
            part = candidate.content.parts[0]

            if hasattr(part, "function_call") and part.function_call.name:
                fc = part.function_call
                function_called = fc.name
                function_args = dict(fc.args) if fc.args else {}

                logger.info(
                    "gemini_function_call",
                    function=function_called,
                    args=function_args,
                )

                # Execute the function via the provided executor
                if function_executor:
                    function_result = await function_executor(function_called, function_args)
                else:
                    function_result = {"error": "No function executor configured"}

                # Track affected devices only on success
                if isinstance(function_result, dict) and function_result.get("success", False):
                    if "device_id" in function_result:
                        devices_affected.append(str(function_result["device_id"]))
                    elif "device_id" in function_args and isinstance(function_args["device_id"], str):
                        devices_affected.append(function_args["device_id"])
                    if "devices" in function_result and isinstance(function_result["devices"], list):
                        for dev_item in function_result["devices"]:
                            if isinstance(dev_item, dict) and "device_id" in dev_item:
                                devices_affected.append(str(dev_item["device_id"]))
                            elif isinstance(dev_item, str):
                                devices_affected.append(dev_item)
                # Deduplicate while preserving order
                devices_affected = list(dict.fromkeys(devices_affected))

                # Send function result back to Gemini for final answer
                function_response = content_types.to_content(
                    genai.protos.Content(
                        parts=[
                            genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=function_called,
                                    response={"result": function_result},
                                )
                            )
                        ]
                    )
                )

                final_response = await self._send_message_async(
                    chat, function_response
                )
                reply = self._extract_text(final_response)
            else:
                # No function call - direct text response
                reply = self._extract_text(response)

            return {
                "reply": reply,
                "function_called": function_called,
                "function_result": function_result,
                "devices_affected": devices_affected,
            }

        except Exception as exc:
            err_str = str(exc)
            # If hit 429 quota, auto switch to next available model in fallback list
            if ("429" in err_str or "quota" in err_str.lower() or "resourceexhausted" in err_str.lower()) and self._current_model_idx + 1 < len(self._fallback_models):
                self._current_model_idx += 1
                new_model = self._fallback_models[self._current_model_idx]
                logger.warning("gemini_quota_switch", switching_to=new_model)
                self._chat_sessions.clear()
                self._init_active_model()
                # Retry call with the new fallback model
                return await self.chat(message, session_id, function_executor)

            logger.exception("gemini_chat_error", error=str(exc))
            self.clear_session(session_id)
            
            # Casual error messages
            if "429" in err_str or "quota" in err_str.lower() or "rate" in err_str.lower():
                user_msg = "Wah lagi rame banget nih, coba lagi bentar ya!"
            elif "not found" in err_str.lower() or "device" in err_str.lower():
                user_msg = "Eh perangkatnya gak ketemu deh, coba cek lagi?"
            elif "timeout" in err_str.lower():
                user_msg = "Aduh lama banget nih, coba lagi dong!"
            else:
                user_msg = "Waduh error nih, coba sekali lagi ya!"

            return {
                "reply": user_msg,
                "function_called": None,
                "function_result": None,
                "devices_affected": [],
            }

    async def _send_message_async(
        self,
        chat: genai.ChatSession,
        message: str | Any,
    ) -> Any:
        """Send a message to Gemini (wraps sync call for async context)."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, chat.send_message, message)

    @staticmethod
    def _extract_text(response: Any) -> str:
        """Extract text content from a Gemini response and make it casual."""
        try:
            if hasattr(response, "text") and response.text and response.text.strip():
                text = response.text.strip()
                return GeminiService._casualize_response(text)
        except (AttributeError, ValueError):
            pass

        try:
            candidates = getattr(response, "candidates", [])
            if candidates:
                parts = getattr(candidates[0].content, "parts", [])
                texts = [p.text.strip() for p in parts if hasattr(p, "text") and p.text and p.text.strip()]
                if texts:
                    combined = " ".join(texts)
                    return GeminiService._casualize_response(combined)
        except Exception:
            pass

        return "Siap, udah beres!"

    @staticmethod
    def _casualize_response(text: str) -> str:
        """Transform formal AI response into casual, natural language."""
        formal_phrases = [
            ("Perintah \"", ""),
            ("\" dipahami dan dieksekusi oleh Smart Home.", " udah beres!"),
            (" dipahami dan dieksekusi oleh Smart Home.", " udah beres!"),
            ("telah berhasil dijalankan", "udah jalan"),
            ("telah berhasil", "udah beres"),
            ("berhasil dijalankan", "udah jalan"),
            ("telah dilakukan", "udah beres"),
            ("telah dinyalakan", "udah nyala"),
            ("telah dimatikan", "udah mati"),
            ("telah diubah", "udah diubah"),
            ("Smart Home", ""),
            ("smart home", ""),
            ("sistem", ""),
            ("perintah", ""),
            ("Perintah", ""),
            ("terdapat", "ada"),
            ("Terdapat", "Ada"),
            ("saat ini", "sekarang"),
            ("Saat ini", "Sekarang"),
            ("Baik, ", ""),
            ("Baiklah, ", ""),
            ("Tentu, ", ""),
            ("Dengan senang hati, ", ""),
        ]
        
        for old, new in formal_phrases:
            text = text.replace(old, new)
        
        # Remove excessive punctuation and whitespace
        text = text.replace("..", ".").replace("  ", " ").strip()
        
        # Truncate overly long responses
        if len(text) > 80:
            sentences = text.split(".")
            if len(sentences) > 2:
                text = ".".join(sentences[:2]).strip() + "!"
        
        return text

    def update_config(
        self,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> bool:
        """Update runtime Gemini configuration and reinitialize."""
        if api_key is not None:
            settings.GEMINI_API_KEY = api_key.strip()
        if model is not None:
            settings.GEMINI_MODEL = model.strip()
        if temperature is not None:
            settings.GEMINI_TEMPERATURE = temperature
        if max_tokens is not None:
            settings.GEMINI_MAX_TOKENS = max_tokens

        self.clear_all_sessions()
        self.initialise()
        return self._initialised

    def clear_session(self, session_id: str) -> None:
        """Remove a chat session's history."""
        if session_id in self._chat_sessions:
            del self._chat_sessions[session_id]
            logger.info("gemini_session_cleared", session_id=session_id)

    def clear_all_sessions(self) -> None:
        """Remove all chat session histories."""
        self._chat_sessions.clear()
        logger.info("gemini_all_sessions_cleared")


# Module-level singleton
gemini_service = GeminiService()
