"use client";

import { useState } from "react";

// TypeScript type for a single horse's input data
type HorseInput = {
  waku: number;
  umaban: number;
  jockey_weight: number;
  horse_weight: number;
  sex: number; // 0: 牡, 1: 牝, 2: セ
  age: number;
};

// TypeScript type for a single prediction result
type Prediction = {
  umaban: number;
  probability: number;
};

// Default horse to add
const createDefaultHorse = (umaban: number): HorseInput => ({
  waku: 1,
  umaban: umaban,
  jockey_weight: 55,
  horse_weight: 480,
  sex: 0,
  age: 4,
});

export default function Home() {
  // State to hold the list of horses to be predicted
  const [horses, setHorses] = useState<HorseInput[]>([
    createDefaultHorse(1), // Start with one default horse
  ]);
  // State to hold the prediction results
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  // State for loading status
  const [isLoading, setIsLoading] = useState(false);
  // State for error messages
  const [error, setError] = useState<string | null>(null);

  // Function to add a new horse to the list
  const addHorse = () => {
    const newUmaban =
      horses.length > 0 ? Math.max(...horses.map((h) => h.umaban)) + 1 : 1;
    setHorses([...horses, createDefaultHorse(newUmaban)]);
  };

  // Function to handle changes in a horse's input fields
  const handleHorseChange = (
    index: number,
    field: keyof HorseInput,
    value: string,
  ) => {
    const newHorses = [...horses];
    // Don't allow changing umaban via this function
    if (field === "umaban") return;
    newHorses[index] = {
      ...newHorses[index],
      [field]: Number(value),
    };
    setHorses(newHorses);
  };

  // Function to remove a horse from the list
  const removeHorse = (index: number) => {
    const newHorses = horses.filter((_, i) => i !== index);
    setHorses(newHorses);
  };

  // Function to call the prediction API
  const handlePredict = async () => {
    setIsLoading(true);
    setError(null);
    setPredictions([]);

    try {
      const response = await fetch("http://127.0.0.1:5000/api/predict", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ horses }),
      });

      if (!response.ok) {
        throw new Error(
          `予測サーバーとの通信に失敗しました (Status: ${response.status})。バックエンドサーバーは起動していますか？`,
        );
      }

      const data = await response.json();
      if (data.error) {
        throw new Error(`予測エラー: ${data.error}`);
      }

      setPredictions(data.predictions);
    } catch (err: unknown) {
      // Use type guarding to safely access the message property
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("不明なエラーが発生しました。");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center bg-gray-50 p-12 font-sans">
      <div className="w-full max-w-5xl">
        <header className="mb-10 text-center">
          <h1 className="text-5xl font-extrabold tracking-tight text-gray-800">
            AI競馬予測
          </h1>
          <p className="mt-2 text-lg text-gray-500">
            過去のレースデータから、各馬が3着以内に入る確率を予測します
          </p>
        </header>

        <div className="mb-8 rounded-xl bg-white p-8 shadow-lg">
          <h2 className="mb-6 text-2xl font-bold text-gray-700">
            予測する馬の情報を入力
          </h2>
          <div className="space-y-4">
            {horses.map((horse, index) => (
              <div
                key={index}
                className="flex flex-wrap items-center gap-4 rounded-lg border bg-gray-50/50 p-4"
              >
                <div className="w-16 text-center text-lg font-bold text-gray-700">
                  馬番 {horse.umaban}
                </div>

                {/* Input fields */}
                <InputGroup
                  label="枠番"
                  value={horse.waku}
                  onChange={(e) =>
                    handleHorseChange(index, "waku", e.target.value)
                  }
                />
                <InputGroup
                  label="斤量"
                  value={horse.jockey_weight}
                  onChange={(e) =>
                    handleHorseChange(index, "jockey_weight", e.target.value)
                  }
                />
                <InputGroup
                  label="馬体重"
                  value={horse.horse_weight}
                  onChange={(e) =>
                    handleHorseChange(index, "horse_weight", e.target.value)
                  }
                />
                <SelectGroup
                  label="性別"
                  value={horse.sex}
                  onChange={(e) =>
                    handleHorseChange(index, "sex", e.target.value)
                  }
                  options={[
                    { value: 0, label: "牡" },
                    { value: 1, label: "牝" },
                    { value: 2, label: "セ" },
                  ]}
                />
                <InputGroup
                  label="年齢"
                  value={horse.age}
                  onChange={(e) =>
                    handleHorseChange(index, "age", e.target.value)
                  }
                />

                <div className="flex flex-grow justify-end">
                  <button
                    onClick={() => removeHorse(index)}
                    className="rounded-md bg-red-500 px-4 py-2 font-bold text-white transition-colors hover:bg-red-600"
                  >
                    削除
                  </button>
                </div>
              </div>
            ))}
          </div>
          <button
            onClick={addHorse}
            className="mt-6 rounded-md bg-blue-500 px-4 py-2 font-bold text-white transition-colors hover:bg-blue-600"
          >
            馬を追加
          </button>
        </div>

        <div className="mb-8 text-center">
          <button
            onClick={handlePredict}
            disabled={isLoading || horses.length === 0}
            className="w-full transform rounded-lg bg-green-600 px-8 py-4 text-xl font-extrabold text-white shadow-lg transition-transform hover:scale-105 hover:bg-green-700 disabled:cursor-not-allowed disabled:bg-gray-400 md:w-1/2"
          >
            {isLoading ? "予測中..." : "予測を実行"}
          </button>
        </div>

        {/* Results section */}
        {error && (
          <div
            className="relative rounded-lg border border-red-400 bg-red-100 px-4 py-3 text-center text-red-700"
            role="alert"
          >
            {error}
          </div>
        )}

        {predictions.length > 0 && (
          <div className="rounded-xl bg-white p-8 shadow-lg">
            <h2 className="mb-6 text-2xl font-bold text-gray-700">
              予測結果 (3着以内に入る確率)
            </h2>
            <ul className="space-y-3">
              {predictions
                .sort((a, b) => b.probability - a.probability)
                .map((pred, idx) => (
                  <li
                    key={pred.umaban}
                    className="flex items-center justify-between rounded-lg bg-gray-100 p-4"
                  >
                    <div className="flex items-center">
                      <span
                        className={`w-8 text-center text-xl font-bold ${
                          idx < 3 ? "text-indigo-600" : "text-gray-500"
                        }`}
                      >
                        {idx + 1}.
                      </span>
                      <span className="text-lg font-semibold text-gray-800">
                        馬番 {pred.umaban}
                      </span>
                    </div>
                    <span className="text-xl font-bold text-indigo-600">
                      {pred.probability.toFixed(2)}%
                    </span>
                  </li>
                ))}
            </ul>
          </div>
        )}
      </div>
    </main>
  );
}

// Helper components for inputs to reduce repetition
const InputGroup = ({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}) => (
  <div className="min-w-[80px] flex-1">
    <label className="block text-sm font-medium text-gray-600">{label}</label>
    <input
      type="number"
      value={value}
      onChange={onChange}
      className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 focus:outline-none sm:text-sm"
    />
  </div>
);

const SelectGroup = ({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: number;
  onChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  options: { value: number; label: string }[];
}) => (
  <div className="min-w-[80px] flex-1">
    <label className="block text-sm font-medium text-gray-600">{label}</label>
    <select
      value={value}
      onChange={onChange}
      className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 focus:outline-none sm:text-sm"
    >
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  </div>
);
