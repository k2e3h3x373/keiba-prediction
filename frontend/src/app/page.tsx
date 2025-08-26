// レース情報の型定義
// TypeScriptを使うことで、データの構造が明確になり、エディタの補完も効くようになります
type Race = {
  id: number;
  name: string;
  venue: string; // 開催地
  date: string;
};

// Next.jsのページコンポーネント
// async/await を使って、サーバーサイドでAPIからデータを取得します
export default async function Home() {
  // バックエンドAPIからレース情報を取得
  // { cache: 'no-store' } を指定することで、常に最新の情報を取得するようになります（開発中に便利）
  const res = await fetch("http://127.0.0.1:5000/api/races", {
    cache: "no-store",
  });
  // 取得したデータをJSON形式に変換し、Race型の配列として型付けします
  const races: Race[] = await res.json();

  return (
    <main className="flex min-h-screen flex-col items-center p-24">
      <h1 className="mb-8 text-4xl font-bold">レース情報一覧</h1>
      <div className="w-full max-w-2xl">
        <div className="overflow-hidden rounded-lg border">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
                >
                  レース名
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
                >
                  開催地
                </th>
                <th
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium tracking-wider text-gray-500 uppercase"
                >
                  開催日
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {races.map((race) => (
                <tr key={race.id}>
                  <td className="px-6 py-4 text-sm font-medium whitespace-nowrap text-gray-900">
                    {race.name}
                  </td>
                  <td className="px-6 py-4 text-sm whitespace-nowrap text-gray-500">
                    {race.venue}
                  </td>
                  <td className="px-6 py-4 text-sm whitespace-nowrap text-gray-500">
                    {race.date}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
