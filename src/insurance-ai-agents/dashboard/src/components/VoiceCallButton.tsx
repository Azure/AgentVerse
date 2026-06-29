import { useState } from 'react';
import { Phone } from 'lucide-react';
import VoiceCallModal from './VoiceCallModal';

/**
 * Floating action button that opens the voice IVR.
 *
 * Always visible bottom-right so the user can trigger it from any tab.
 * Hidden when the modal is open to avoid two phone icons fighting for
 * attention.
 */
export default function VoiceCallButton() {
  const [open, setOpen] = useState(false);
  return (
    <>
      {!open && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          title="Llamar al asistente de voz"
          className="fixed bottom-6 right-6 z-[60] inline-flex items-center gap-3 rounded-full bg-primary-600 px-5 py-3 text-sm font-semibold text-white shadow-xl ring-4 ring-primary-100 transition-transform hover:scale-105 hover:bg-primary-700"
        >
          <span className="relative grid h-9 w-9 place-items-center rounded-full bg-white/20">
            <Phone className="h-5 w-5" />
            <span className="absolute -right-0.5 -top-0.5 h-3 w-3 animate-pulse rounded-full bg-emerald-400 ring-2 ring-primary-600" />
          </span>
          <span>Hablar con asistente</span>
        </button>
      )}
      <VoiceCallModal open={open} onClose={() => setOpen(false)} />
    </>
  );
}
