import { Html, Head, Main, NextScript } from 'next/document';

export default function Document() {
  return (
    <Html lang="zh-CN">
      <Head>
        <meta charSet="utf-8" />
        <meta name="description" content="企业级智能大数据管理平台" />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
