import { int, mysqlEnum, mysqlTable, text, timestamp, varchar } from "drizzle-orm/mysql-core";

/**
 * Core user table backing auth flow.
 * Extend this file with additional tables as your product grows.
 * Columns use camelCase to match both database fields and generated types.
 */
export const users = mysqlTable("users", {
  /**
   * Surrogate primary key. Auto-incremented numeric value managed by the database.
   * Use this for relations between tables.
   */
  id: int("id").autoincrement().primaryKey(),
  /** Manus OAuth identifier (openId) returned from the OAuth callback. Unique per user. */
  openId: varchar("openId", { length: 64 }).notNull().unique(),
  name: text("name"),
  email: varchar("email", { length: 320 }),
  loginMethod: varchar("loginMethod", { length: 64 }),
  role: mysqlEnum("role", ["user", "admin"]).default("user").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
  lastSignedIn: timestamp("lastSignedIn").defaultNow().notNull(),
});

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;

/**
 * ============================================
 * MODULE 2: VIDEO MANAGEMENT TABLES
 * ============================================
 * Các bảng quản lý video và metadata
 */

/** 
 * Bảng categories - Danh mục video (Phim, Bài giảng, Podcast, v.v.)
 */
export const categories = mysqlTable("categories", {
  id: int("id").autoincrement().primaryKey(),
  name: varchar("name", { length: 100 }).notNull(),
  slug: varchar("slug", { length: 100 }).notNull().unique(),
  description: text("description"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export type Category = typeof categories.$inferSelect;
export type InsertCategory = typeof categories.$inferInsert;

/**
 * Bảng videos - Lưu trữ thông tin video
 * Mỗi video có thể thuộc nhiều category và có level (A1, A2, B1, B2, C1, C2)
 */
export const videos = mysqlTable("videos", {
  id: int("id").autoincrement().primaryKey(),
  
  /** Thông tin cơ bản */
  title: varchar("title", { length: 255 }).notNull(),
  slug: varchar("slug", { length: 255 }).notNull().unique(),
  description: text("description"),
  
  /** File video trên S3 */
  videoUrl: text("videoUrl").notNull(), // URL đầy đủ từ S3
  videoKey: varchar("videoKey", { length: 500 }).notNull(), // Key trong S3 bucket
  thumbnailUrl: text("thumbnailUrl"), // Ảnh thumbnail
  
  /** Metadata */
  duration: int("duration"), // Thời lượng video (giây)
  level: mysqlEnum("level", ["A1", "A2", "B1", "B2", "C1", "C2"]).notNull(), // Trình độ
  language: varchar("language", { length: 10 }).default("en").notNull(), // Ngôn ngữ gốc
  
  /** Quan hệ */
  categoryId: int("categoryId").references(() => categories.id),
  uploadedBy: int("uploadedBy").references(() => users.id).notNull(),
  
  /** Trạng thái */
  status: mysqlEnum("status", ["draft", "processing", "published", "archived"]).default("draft").notNull(),
  viewCount: int("viewCount").default(0).notNull(),
  
  /** Timestamps */
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
  publishedAt: timestamp("publishedAt"),
});

export type Video = typeof videos.$inferSelect;
export type InsertVideo = typeof videos.$inferInsert;

/**
 * Bảng subtitles - Lưu trữ phụ đề cho video
 * Mỗi video có thể có nhiều phụ đề (nhiều ngôn ngữ)
 */
export const subtitles = mysqlTable("subtitles", {
  id: int("id").autoincrement().primaryKey(),
  videoId: int("videoId").references(() => videos.id).notNull(),
  
  /** Thông tin phụ đề */
  language: varchar("language", { length: 10 }).notNull(), // vi, en, zh, ja, v.v.
  languageName: varchar("languageName", { length: 50 }).notNull(), // Vietnamese, English, v.v.
  
  /** File phụ đề trên S3 */
  subtitleUrl: text("subtitleUrl").notNull(), // URL file .vtt
  subtitleKey: varchar("subtitleKey", { length: 500 }).notNull(), // Key trong S3
  
  /** Metadata */
  isDefault: int("isDefault").default(0).notNull(), // 1 = phụ đề mặc định
  source: mysqlEnum("source", ["manual", "ai_generated", "imported"]).default("manual").notNull(),
  
  /** Timestamps */
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type Subtitle = typeof subtitles.$inferSelect;
export type InsertSubtitle = typeof subtitles.$inferInsert;

/**
 * ============================================
 * MODULE 5: VOCABULARY MANAGEMENT TABLES
 * ============================================
 * Bảng lưu từ vựng người dùng đã lưu
 */

/**
 * Bảng user_vocabulary - Từ vựng người dùng đã lưu
 */
export const userVocabulary = mysqlTable("user_vocabulary", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").references(() => users.id).notNull(),
  
  /** Thông tin từ vựng */
  word: varchar("word", { length: 200 }).notNull(),
  translation: text("translation"), // Nghĩa tiếng Việt
  phonetic: varchar("phonetic", { length: 100 }), // Phiên âm
  definition: text("definition"), // Định nghĩa tiếng Anh
  example: text("example"), // Câu ví dụ
  
  /** Context từ video */
  videoId: int("videoId").references(() => videos.id),
  timestamp: int("timestamp"), // Thời điểm trong video (giây)
  context: text("context"), // Câu chứa từ trong video
  
  /** Trạng thái học tập */
  masteryLevel: int("masteryLevel").default(0).notNull(), // 0-5: mức độ thuộc từ
  reviewCount: int("reviewCount").default(0).notNull(),
  lastReviewedAt: timestamp("lastReviewedAt"),
  
  /** Timestamps */
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export type UserVocabulary = typeof userVocabulary.$inferSelect;
export type InsertUserVocabulary = typeof userVocabulary.$inferInsert;