// リッチメニューを作成してデフォルト設定するスクリプト。
// 実行: LINE_CHANNEL_ACCESS_TOKEN=xxxx node create-richmenu.mjs
//
// 各ボタンのリンク先は下の LINKS を実際のURLに書き換えてから実行すること。

const CHANNEL_ACCESS_TOKEN = process.env.LINE_CHANNEL_ACCESS_TOKEN;
if (!CHANNEL_ACCESS_TOKEN) {
  console.error("環境変数 LINE_CHANNEL_ACCESS_TOKEN を設定してください");
  process.exit(1);
}

// TODO: それぞれ実際のURLに置き換える
const LINKS = {
  freeConsultation: "https://example.com/reservation", // 無料相談＝予約ページ（freee予約のURL）
  joinFlow: "https://example.com/flow",                // 入会の流れ
  pricing: "https://example.com/pricing",               // 料金プラン
  features: "https://example.com/features",             // 特徴
  staff: "https://example.com/staff",                   // スタッフ紹介
  faq: "https://example.com/faq",                        // よくある質問
};

const COL = [0, 834, 1667];
const COL_W = [834, 833, 833];
const ROW = [0, 843];
const ROW_H = 843;

function area(colIndex, rowIndex, uri) {
  return {
    bounds: { x: COL[colIndex], y: ROW[rowIndex], width: COL_W[colIndex], height: ROW_H },
    action: { type: "uri", uri },
  };
}

const richMenuObject = {
  size: { width: 2500, height: 1686 },
  selected: true,
  name: "婚活相談所メインメニュー",
  chatBarText: "メニュー",
  areas: [
    area(0, 0, LINKS.freeConsultation),
    area(1, 0, LINKS.joinFlow),
    area(2, 0, LINKS.pricing),
    area(0, 1, LINKS.features),
    area(1, 1, LINKS.staff),
    area(2, 1, LINKS.faq),
  ],
};

async function main() {
  // 1. リッチメニューを作成
  const createRes = await fetch("https://api.line.me/v2/bot/richmenu", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${CHANNEL_ACCESS_TOKEN}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(richMenuObject),
  });
  if (!createRes.ok) {
    throw new Error(`リッチメニュー作成失敗: ${createRes.status} ${await createRes.text()}`);
  }
  const { richMenuId } = await createRes.json();
  console.log("richMenuId:", richMenuId);

  // 2. 画像をアップロード
  const fs = await import("node:fs");
  const imageBuffer = fs.readFileSync(new URL("./assets/richmenu.png", import.meta.url));
  const uploadRes = await fetch(`https://api-data.line.me/v2/bot/richmenu/${richMenuId}/content`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${CHANNEL_ACCESS_TOKEN}`,
      "Content-Type": "image/png",
    },
    body: imageBuffer,
  });
  if (!uploadRes.ok) {
    throw new Error(`画像アップロード失敗: ${uploadRes.status} ${await uploadRes.text()}`);
  }
  console.log("画像アップロード完了");

  // 3. 全ユーザーのデフォルトリッチメニューに設定
  const defaultRes = await fetch(`https://api.line.me/v2/bot/user/all/richmenu/${richMenuId}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${CHANNEL_ACCESS_TOKEN}` },
  });
  if (!defaultRes.ok) {
    throw new Error(`デフォルト設定失敗: ${defaultRes.status} ${await defaultRes.text()}`);
  }
  console.log("デフォルトリッチメニューとして設定完了");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
