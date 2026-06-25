"use client";

const defaultQuestions = [
  "Bugun qancha savdo bo'ldi?",
  "Bugungi tushum qancha?",
  "Coca-Cola qoldig'i qancha?",
  "Pepsi narxi qancha?",
  "Qaysi mahsulotlar kam qolgan?",
  "Eng ko'p sotilgan mahsulot qaysi?",
  "Bu oy savdo qancha?",
  "Nima qila olasan?",
];

type AISuggestedQuestionsProps = {
  questions?: string[];
  disabled?: boolean;
  onSelect: (question: string) => void;
};

export function getDefaultAIQuestions() {
  return defaultQuestions;
}

export function AISuggestedQuestions({
  questions = defaultQuestions,
  disabled = false,
  onSelect,
}: AISuggestedQuestionsProps) {
  const visibleQuestions = questions.length ? questions : defaultQuestions;

  return (
    <div className="grid gap-2">
      <div className="text-xs font-black uppercase text-slate-500">
        Tavsiya savollar
      </div>
      <div className="flex flex-wrap gap-2">
        {visibleQuestions.map((question) => (
          <button
            key={question}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(question)}
            className="min-h-9 rounded border border-slate-200 bg-white px-3 py-2 text-left text-xs font-bold text-slate-700 shadow-panel transition hover:border-blue-300 hover:bg-blue-50 hover:text-blue-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}
