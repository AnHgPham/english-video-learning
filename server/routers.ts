import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { publicProcedure, router, protectedProcedure } from "./_core/trpc";
import { TRPCError } from "@trpc/server";
import { z } from "zod";

export const appRouter = router({
    // if you need to use socket.io, read and register route in server/_core/index.ts, all api should start with '/api/' so that the gateway can route correctly
  system: systemRouter,
  auth: router({
    me: publicProcedure.query(opts => opts.ctx.user),
    logout: publicProcedure.mutation(({ ctx }) => {
      const cookieOptions = getSessionCookieOptions(ctx.req);
      ctx.res.clearCookie(COOKIE_NAME, { ...cookieOptions, maxAge: -1 });
      return {
        success: true,
      } as const;
    }),
  }),

  /**
   * ============================================
   * MODULE 2: VIDEO MANAGEMENT ROUTERS
   * ============================================
   */
  video: router({
    /**
     * 2.1 - Lấy danh sách video (public - cho user xem)
     */
    list: publicProcedure
      .input(z.object({
        level: z.enum(["A1", "A2", "B1", "B2", "C1", "C2"]).optional(),
        categoryId: z.number().optional(),
        search: z.string().optional(),
        limit: z.number().default(20),
        offset: z.number().default(0),
      }).optional())
      .query(async ({ input }) => {
        const { getVideos } = await import("./db");
        return await getVideos({
          status: "published", // Chỉ hiển thị video đã publish
          ...input,
        });
      }),

    /**
     * 2.2 - Lấy chi tiết video theo slug
     */
    getBySlug: publicProcedure
      .input(z.object({
        slug: z.string(),
      }))
      .query(async ({ input }) => {
        const { getVideoBySlug, incrementVideoViewCount } = await import("./db");
        const video = await getVideoBySlug(input.slug);
        
        // Tăng view count
        if (video) {
          await incrementVideoViewCount(video.id);
        }
        
        return video;
      }),

    /**
     * 2.3 - Lấy phụ đề của video
     */
    getSubtitles: publicProcedure
      .input(z.object({
        videoId: z.number(),
      }))
      .query(async ({ input }) => {
        const { getSubtitlesByVideoId } = await import("./db");
        return await getSubtitlesByVideoId(input.videoId);
      }),

    /**
     * 2.4 - Lấy danh sách categories
     */
    getCategories: publicProcedure
      .query(async () => {
        const { getAllCategories } = await import("./db");
        return await getAllCategories();
      }),
  }),

  /**
   * ============================================
   * MODULE 2: ADMIN VIDEO MANAGEMENT ROUTERS
   * ============================================
   * Các router chỉ dành cho admin
   */
  admin: router({
    /**
     * 2.5 - Lấy danh sách tất cả video (bao gồm draft)
     */
    listAllVideos: protectedProcedure
      .input(z.object({
        status: z.enum(["draft", "processing", "published", "archived"]).optional(),
        level: z.enum(["A1", "A2", "B1", "B2", "C1", "C2"]).optional(),
        categoryId: z.number().optional(),
        search: z.string().optional(),
        limit: z.number().default(20),
        offset: z.number().default(0),
      }).optional())
      .query(async ({ ctx, input }) => {
        // Kiểm tra quyền admin
        if (ctx.user.role !== "admin") {
          throw new TRPCError({ code: "FORBIDDEN", message: "Only admin can access this" });
        }
        
        const { getVideos } = await import("./db");
        return await getVideos(input || {});
      }),

    /**
     * 2.6 - Tạo video mới
     */
    createVideo: protectedProcedure
      .input(z.object({
        title: z.string().min(1),
        slug: z.string().min(1),
        description: z.string().optional(),
        videoUrl: z.string().url(),
        videoKey: z.string(),
        thumbnailUrl: z.string().url().optional(),
        duration: z.number().optional(),
        level: z.enum(["A1", "A2", "B1", "B2", "C1", "C2"]),
        language: z.string().default("en"),
        categoryId: z.number().optional(),
        status: z.enum(["draft", "processing", "published", "archived"]).default("draft"),
      }))
      .mutation(async ({ ctx, input }) => {
        // Kiểm tra quyền admin
        if (ctx.user.role !== "admin") {
          throw new TRPCError({ code: "FORBIDDEN", message: "Only admin can create videos" });
        }
        
        const { createVideo } = await import("./db");
        return await createVideo({
          ...input,
          uploadedBy: ctx.user.id,
        });
      }),

    /**
     * 2.7 - Cập nhật video
     */
    updateVideo: protectedProcedure
      .input(z.object({
        id: z.number(),
        title: z.string().min(1).optional(),
        slug: z.string().min(1).optional(),
        description: z.string().optional(),
        thumbnailUrl: z.string().url().optional(),
        duration: z.number().optional(),
        level: z.enum(["A1", "A2", "B1", "B2", "C1", "C2"]).optional(),
        language: z.string().optional(),
        categoryId: z.number().optional(),
        status: z.enum(["draft", "processing", "published", "archived"]).optional(),
      }))
      .mutation(async ({ ctx, input }) => {
        // Kiểm tra quyền admin
        if (ctx.user.role !== "admin") {
          throw new TRPCError({ code: "FORBIDDEN", message: "Only admin can update videos" });
        }
        
        const { id, ...data } = input;
        const { updateVideo } = await import("./db");
        const success = await updateVideo(id, data);
        
        if (!success) {
          throw new TRPCError({ code: "INTERNAL_SERVER_ERROR", message: "Failed to update video" });
        }
        
        return { success: true };
      }),

    /**
     * 2.8 - Xóa video
     */
    deleteVideo: protectedProcedure
      .input(z.object({
        id: z.number(),
      }))
      .mutation(async ({ ctx, input }) => {
        // Kiểm tra quyền admin
        if (ctx.user.role !== "admin") {
          throw new TRPCError({ code: "FORBIDDEN", message: "Only admin can delete videos" });
        }
        
        const { deleteVideo } = await import("./db");
        const success = await deleteVideo(input.id);
        
        if (!success) {
          throw new TRPCError({ code: "INTERNAL_SERVER_ERROR", message: "Failed to delete video" });
        }
        
        return { success: true };
      }),
  }),
});

export type AppRouter = typeof appRouter;
