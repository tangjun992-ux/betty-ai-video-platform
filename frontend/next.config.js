/** @type {import('next').NextConfig} */
// 服务端代理目标：Docker 内前端容器需通过服务名访问后端（localhost 在容器里指向自己）。
// 本地裸跑 next dev 时回退到 localhost:8000。
const INTERNAL_API_URL = process.env.INTERNAL_API_URL || 'http://localhost:8000';

const nextConfig = {
  images: {
    domains: ['localhost'],
    remotePatterns: [
      { protocol: 'http', hostname: 'localhost', port: '8000' },
    ],
  },
  // Docker/WSL2 挂载目录 inotify 失效 → 用轮询保证 Windows 侧编辑可热更新
  webpack: (config, { dev }) => {
    if (dev) {
      config.watchOptions = {
        poll: 1200,
        aggregateTimeout: 300,
        ignored: ['**/node_modules/**', '**/.next/**'],
      };
    }
    return config;
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${INTERNAL_API_URL}/api/:path*`,
      },
    ];
  },
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on',
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=63072000; includeSubDomains; preload',
          },
          {
            key: 'X-Frame-Options',
            value: 'SAMEORIGIN',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'origin-when-cross-origin',
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=()',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
