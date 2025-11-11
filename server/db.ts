import { eq } from "drizzle-orm";
import { drizzle } from "drizzle-orm/mysql2";
import { InsertUser, users } from "../drizzle/schema";
import { ENV } from './_core/env';

let _db: ReturnType<typeof drizzle> | null = null;

// Lazily create the drizzle instance so local tooling can run without a DB.
export async function getDb() {
  if (!_db && process.env.DATABASE_URL) {
    try {
      _db = drizzle(process.env.DATABASE_URL);
    } catch (error) {
      console.warn("[Database] Failed to connect:", error);
      _db = null;
    }
  }
  return _db;
}

export async function upsertUser(user: InsertUser): Promise<void> {
  if (!user.openId) {
    throw new Error("User openId is required for upsert");
  }

  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot upsert user: database not available");
    return;
  }

  try {
    const values: InsertUser = {
      openId: user.openId,
    };
    const updateSet: Record<string, unknown> = {};

    const textFields = ["name", "email", "loginMethod"] as const;
    type TextField = (typeof textFields)[number];

    const assignNullable = (field: TextField) => {
      const value = user[field];
      if (value === undefined) return;
      const normalized = value ?? null;
      values[field] = normalized;
      updateSet[field] = normalized;
    };

    textFields.forEach(assignNullable);

    if (user.lastSignedIn !== undefined) {
      values.lastSignedIn = user.lastSignedIn;
      updateSet.lastSignedIn = user.lastSignedIn;
    }
    if (user.role !== undefined) {
      values.role = user.role;
      updateSet.role = user.role;
    } else if (user.openId === ENV.ownerOpenId) {
      values.role = 'admin';
      updateSet.role = 'admin';
    }

    if (!values.lastSignedIn) {
      values.lastSignedIn = new Date();
    }

    if (Object.keys(updateSet).length === 0) {
      updateSet.lastSignedIn = new Date();
    }

    await db.insert(users).values(values).onDuplicateKeyUpdate({
      set: updateSet,
    });
  } catch (error) {
    console.error("[Database] Failed to upsert user:", error);
    throw error;
  }
}

export async function getUserByOpenId(openId: string) {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot get user: database not available");
    return undefined;
  }

  const result = await db.select().from(users).where(eq(users.openId, openId)).limit(1);

  return result.length > 0 ? result[0] : undefined;
}

/**
 * ============================================
 * MODULE 2: VIDEO MANAGEMENT HELPERS
 * ============================================
 */

import { categories, videos, subtitles, Category, Video, Subtitle, InsertVideo, InsertSubtitle } from "../drizzle/schema";
import { desc, and, like, or } from "drizzle-orm";

/**
 * 2.1 - Lấy danh sách tất cả categories
 */
export async function getAllCategories(): Promise<Category[]> {
  const db = await getDb();
  if (!db) return [];
  
  try {
    return await db.select().from(categories).orderBy(categories.name);
  } catch (error) {
    console.error("[Database] Failed to get categories:", error);
    return [];
  }
}

/**
 * 2.2 - Lấy danh sách video (có phân trang và lọc)
 */
export async function getVideos(params: {
  status?: "draft" | "processing" | "published" | "archived";
  level?: "A1" | "A2" | "B1" | "B2" | "C1" | "C2";
  categoryId?: number;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<Video[]> {
  const db = await getDb();
  if (!db) return [];
  
  try {
    let query = db.select().from(videos);
    
    // Apply filters
    const conditions = [];
    if (params.status) {
      conditions.push(eq(videos.status, params.status));
    }
    if (params.level) {
      conditions.push(eq(videos.level, params.level));
    }
    if (params.categoryId) {
      conditions.push(eq(videos.categoryId, params.categoryId));
    }
    if (params.search) {
      conditions.push(
        or(
          like(videos.title, `%${params.search}%`),
          like(videos.description, `%${params.search}%`)
        )
      );
    }
    
    if (conditions.length > 0) {
      query = query.where(and(...conditions)) as any;
    }
    
    // Order by newest first
    query = query.orderBy(desc(videos.createdAt)) as any;
    
    // Pagination
    if (params.limit) {
      query = query.limit(params.limit) as any;
    }
    if (params.offset) {
      query = query.offset(params.offset) as any;
    }
    
    return await query;
  } catch (error) {
    console.error("[Database] Failed to get videos:", error);
    return [];
  }
}

/**
 * 2.3 - Lấy chi tiết một video theo ID
 */
export async function getVideoById(id: number): Promise<Video | undefined> {
  const db = await getDb();
  if (!db) return undefined;
  
  try {
    const result = await db.select().from(videos).where(eq(videos.id, id)).limit(1);
    return result[0];
  } catch (error) {
    console.error("[Database] Failed to get video:", error);
    return undefined;
  }
}

/**
 * 2.4 - Lấy chi tiết một video theo slug
 */
export async function getVideoBySlug(slug: string): Promise<Video | undefined> {
  const db = await getDb();
  if (!db) return undefined;
  
  try {
    const result = await db.select().from(videos).where(eq(videos.slug, slug)).limit(1);
    return result[0];
  } catch (error) {
    console.error("[Database] Failed to get video by slug:", error);
    return undefined;
  }
}

/**
 * 2.5 - Tạo video mới
 */
export async function createVideo(data: InsertVideo): Promise<Video | undefined> {
  const db = await getDb();
  if (!db) return undefined;
  
  try {
    const result = await db.insert(videos).values(data);
    const insertId = Number(result[0].insertId);
    return await getVideoById(insertId);
  } catch (error) {
    console.error("[Database] Failed to create video:", error);
    return undefined;
  }
}

/**
 * 2.6 - Cập nhật video
 */
export async function updateVideo(id: number, data: Partial<InsertVideo>): Promise<boolean> {
  const db = await getDb();
  if (!db) return false;
  
  try {
    await db.update(videos).set(data).where(eq(videos.id, id));
    return true;
  } catch (error) {
    console.error("[Database] Failed to update video:", error);
    return false;
  }
}

/**
 * 2.7 - Xóa video
 */
export async function deleteVideo(id: number): Promise<boolean> {
  const db = await getDb();
  if (!db) return false;
  
  try {
    await db.delete(videos).where(eq(videos.id, id));
    return true;
  } catch (error) {
    console.error("[Database] Failed to delete video:", error);
    return false;
  }
}

/**
 * 2.8 - Lấy phụ đề của video
 */
export async function getSubtitlesByVideoId(videoId: number): Promise<Subtitle[]> {
  const db = await getDb();
  if (!db) return [];
  
  try {
    return await db.select().from(subtitles).where(eq(subtitles.videoId, videoId));
  } catch (error) {
    console.error("[Database] Failed to get subtitles:", error);
    return [];
  }
}

/**
 * 2.9 - Tăng view count cho video
 */
export async function incrementVideoViewCount(id: number): Promise<boolean> {
  const db = await getDb();
  if (!db) return false;
  
  try {
    const video = await getVideoById(id);
    if (!video) return false;
    
    await db.update(videos)
      .set({ viewCount: (video.viewCount || 0) + 1 })
      .where(eq(videos.id, id));
    return true;
  } catch (error) {
    console.error("[Database] Failed to increment view count:", error);
    return false;
  }
}
