import type { MetadataRoute } from "next";

const baseUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://betty.ai";

// Static routes with their priorities and change frequencies
const staticRoutes: MetadataRoute.Sitemap = [
  { url: baseUrl, lastModified: new Date(), changeFrequency: "daily", priority: 1.0 },
  { url: `${baseUrl}/create/image`, lastModified: new Date(), changeFrequency: "weekly", priority: 0.9 },
  { url: `${baseUrl}/create/video`, lastModified: new Date(), changeFrequency: "weekly", priority: 0.9 },
  { url: `${baseUrl}/create/lipsync`, lastModified: new Date(), changeFrequency: "weekly", priority: 0.8 },
  { url: `${baseUrl}/create/motion`, lastModified: new Date(), changeFrequency: "weekly", priority: 0.8 },
  { url: `${baseUrl}/create/timeline`, lastModified: new Date(), changeFrequency: "weekly", priority: 0.8 },
  { url: `${baseUrl}/agent`, lastModified: new Date(), changeFrequency: "weekly", priority: 0.8 },
  { url: `${baseUrl}/gallery`, lastModified: new Date(), changeFrequency: "daily", priority: 0.7 },
  { url: `${baseUrl}/library`, lastModified: new Date(), changeFrequency: "daily", priority: 0.7 },
  { url: `${baseUrl}/tools`, lastModified: new Date(), changeFrequency: "weekly", priority: 0.7 },
  { url: `${baseUrl}/pricing`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.8 },
  { url: `${baseUrl}/models`, lastModified: new Date(), changeFrequency: "weekly", priority: 0.6 },
  { url: `${baseUrl}/settings`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.3 },
  { url: `${baseUrl}/auth/login`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.4 },
  { url: `${baseUrl}/auth/register`, lastModified: new Date(), changeFrequency: "monthly", priority: 0.4 },
  { url: `${baseUrl}/tasks`, lastModified: new Date(), changeFrequency: "daily", priority: 0.5 },
  { url: `${baseUrl}/dashboard`, lastModified: new Date(), changeFrequency: "daily", priority: 0.5 },
];

export default function sitemap(): MetadataRoute.Sitemap {
  return staticRoutes;
}
