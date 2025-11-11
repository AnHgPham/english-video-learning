/**
 * ============================================
 * MODULE 2: ADMIN DASHBOARD
 * ============================================
 * Trang quản lý video dành cho Admin
 * Chức năng: Upload, Edit, Delete video
 */

import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { trpc } from "@/lib/trpc";
import { ArrowLeft, Edit, Eye, Plus, Trash2, Upload, Video } from "lucide-react";
import { useState } from "react";
import { Link, useLocation } from "wouter";
import { toast } from "sonner";

export default function AdminDashboard() {
  const { user, isAuthenticated } = useAuth();
  const [, setLocation] = useLocation();
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    title: "",
    slug: "",
    description: "",
    level: "A1" as const,
    language: "en",
    videoFile: null as File | null,
    thumbnailFile: null as File | null,
  });

  // Kiểm tra quyền admin
  if (!isAuthenticated || user?.role !== "admin") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle>Không có quyền truy cập</CardTitle>
            <CardDescription>
              Bạn cần đăng nhập với tài khoản Admin để truy cập trang này.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/">
              <Button className="w-full">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Quay về trang chủ
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Lấy danh sách tất cả video (bao gồm draft)
  const { data: videos = [], isLoading, refetch } = trpc.admin.listAllVideos.useQuery();

  // Mutation để xóa video
  const deleteVideoMutation = trpc.admin.deleteVideo.useMutation({
    onSuccess: () => {
      toast.success("Đã xóa video thành công!");
      refetch();
    },
    onError: (error) => {
      toast.error(`Lỗi: ${error.message}`);
    },
  });

  // Xử lý xóa video
  const handleDeleteVideo = async (id: number, title: string) => {
    if (confirm(`Bạn có chắc chắn muốn xóa video "${title}"?`)) {
      deleteVideoMutation.mutate({ id });
    }
  };

  // Xử lý upload video (sẽ implement sau)
  const handleUploadVideo = async () => {
    if (!formData.title || !formData.slug || !formData.videoFile) {
      toast.error("Vui lòng điền đầy đủ thông tin và chọn file video!");
      return;
    }

    setIsUploading(true);
    
    try {
      // TODO: Implement upload to S3 và create video
      toast.info("Chức năng upload video sẽ được triển khai trong giai đoạn tiếp theo");
      setIsUploadDialogOpen(false);
    } catch (error) {
      toast.error("Có lỗi xảy ra khi upload video");
    } finally {
      setIsUploading(false);
    }
  };

  // Tự động tạo slug từ title
  const handleTitleChange = (title: string) => {
    setFormData({
      ...formData,
      title,
      slug: title
        .toLowerCase()
        .replace(/[^a-z0-9\s-]/g, "")
        .replace(/\s+/g, "-")
        .replace(/-+/g, "-")
        .trim(),
    });
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/">
                <Button variant="ghost" size="sm">
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Quay lại
                </Button>
              </Link>
              <div>
                <h1 className="text-xl font-bold text-foreground">Admin Dashboard</h1>
                <p className="text-sm text-muted-foreground">Quản lý video học tiếng Anh</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">
                Xin chào, <strong>{user?.name}</strong>
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Tổng số video</CardDescription>
              <CardTitle className="text-3xl">{videos.length}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Đã xuất bản</CardDescription>
              <CardTitle className="text-3xl text-green-600">
                {videos.filter((v) => v.status === "published").length}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Bản nháp</CardDescription>
              <CardTitle className="text-3xl text-yellow-600">
                {videos.filter((v) => v.status === "draft").length}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Tổng lượt xem</CardDescription>
              <CardTitle className="text-3xl text-blue-600">
                {videos.reduce((sum, v) => sum + (v.viewCount || 0), 0)}
              </CardTitle>
            </CardHeader>
          </Card>
        </div>

        {/* Video Management */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Quản lý Video</CardTitle>
                <CardDescription>Danh sách tất cả video trong hệ thống</CardDescription>
              </div>

              <Dialog open={isUploadDialogOpen} onOpenChange={setIsUploadDialogOpen}>
                <DialogTrigger asChild>
                  <Button>
                    <Plus className="h-4 w-4 mr-2" />
                    Thêm Video Mới
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                  <DialogHeader>
                    <DialogTitle>Thêm Video Mới</DialogTitle>
                    <DialogDescription>
                      Điền thông tin và upload video học tiếng Anh
                    </DialogDescription>
                  </DialogHeader>

                  <div className="space-y-4 py-4">
                    {/* Title */}
                    <div className="space-y-2">
                      <Label htmlFor="title">Tiêu đề video *</Label>
                      <Input
                        id="title"
                        placeholder="Ví dụ: Learn English with Friends - Episode 1"
                        value={formData.title}
                        onChange={(e) => handleTitleChange(e.target.value)}
                      />
                    </div>

                    {/* Slug */}
                    <div className="space-y-2">
                      <Label htmlFor="slug">Slug (URL) *</Label>
                      <Input
                        id="slug"
                        placeholder="learn-english-with-friends-episode-1"
                        value={formData.slug}
                        onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                      />
                      <p className="text-xs text-muted-foreground">
                        URL sẽ là: /watch/{formData.slug || "slug-cua-video"}
                      </p>
                    </div>

                    {/* Description */}
                    <div className="space-y-2">
                      <Label htmlFor="description">Mô tả</Label>
                      <Textarea
                        id="description"
                        placeholder="Mô tả ngắn về nội dung video..."
                        rows={3}
                        value={formData.description}
                        onChange={(e) =>
                          setFormData({ ...formData, description: e.target.value })
                        }
                      />
                    </div>

                    {/* Level & Language */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="level">Trình độ *</Label>
                        <Select
                          value={formData.level}
                          onValueChange={(value: any) =>
                            setFormData({ ...formData, level: value })
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="A1">A1 - Sơ cấp</SelectItem>
                            <SelectItem value="A2">A2 - Tiền trung cấp</SelectItem>
                            <SelectItem value="B1">B1 - Trung cấp</SelectItem>
                            <SelectItem value="B2">B2 - Trung cấp cao</SelectItem>
                            <SelectItem value="C1">C1 - Nâng cao</SelectItem>
                            <SelectItem value="C2">C2 - Thành thạo</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="language">Ngôn ngữ</Label>
                        <Select
                          value={formData.language}
                          onValueChange={(value) =>
                            setFormData({ ...formData, language: value })
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="en">English</SelectItem>
                            <SelectItem value="vi">Tiếng Việt</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    {/* Video File */}
                    <div className="space-y-2">
                      <Label htmlFor="video">File Video *</Label>
                      <Input
                        id="video"
                        type="file"
                        accept="video/*"
                        onChange={(e) =>
                          setFormData({ ...formData, videoFile: e.target.files?.[0] || null })
                        }
                      />
                      <p className="text-xs text-muted-foreground">
                        Định dạng: MP4, WebM, MOV (tối đa 500MB)
                      </p>
                    </div>

                    {/* Thumbnail File */}
                    <div className="space-y-2">
                      <Label htmlFor="thumbnail">Ảnh Thumbnail (tùy chọn)</Label>
                      <Input
                        id="thumbnail"
                        type="file"
                        accept="image/*"
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            thumbnailFile: e.target.files?.[0] || null,
                          })
                        }
                      />
                      <p className="text-xs text-muted-foreground">
                        Định dạng: JPG, PNG (khuyến nghị 1280x720px)
                      </p>
                    </div>
                  </div>

                  <DialogFooter>
                    <Button
                      variant="outline"
                      onClick={() => setIsUploadDialogOpen(false)}
                      disabled={isUploading}
                    >
                      Hủy
                    </Button>
                    <Button onClick={handleUploadVideo} disabled={isUploading}>
                      {isUploading ? (
                        <>
                          <Upload className="h-4 w-4 mr-2 animate-spin" />
                          Đang upload...
                        </>
                      ) : (
                        <>
                          <Upload className="h-4 w-4 mr-2" />
                          Upload Video
                        </>
                      )}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </div>
          </CardHeader>

          <CardContent>
            {isLoading ? (
              <div className="text-center py-8">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                <p className="mt-2 text-sm text-muted-foreground">Đang tải...</p>
              </div>
            ) : videos.length === 0 ? (
              <div className="text-center py-16">
                <Video className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">Chưa có video nào</h3>
                <p className="text-muted-foreground mb-4">
                  Bắt đầu bằng cách thêm video đầu tiên của bạn
                </p>
                <Button onClick={() => setIsUploadDialogOpen(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Thêm Video Mới
                </Button>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Tiêu đề</TableHead>
                    <TableHead>Trình độ</TableHead>
                    <TableHead>Trạng thái</TableHead>
                    <TableHead>Lượt xem</TableHead>
                    <TableHead>Ngày tạo</TableHead>
                    <TableHead className="text-right">Thao tác</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {videos.map((video) => (
                    <TableRow key={video.id}>
                      <TableCell className="font-medium">{video.title}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{video.level}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            video.status === "published"
                              ? "default"
                              : video.status === "draft"
                              ? "secondary"
                              : "outline"
                          }
                        >
                          {video.status === "published"
                            ? "Đã xuất bản"
                            : video.status === "draft"
                            ? "Bản nháp"
                            : video.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Eye className="h-4 w-4 text-muted-foreground" />
                          {video.viewCount || 0}
                        </div>
                      </TableCell>
                      <TableCell>
                        {new Date(video.createdAt).toLocaleDateString("vi-VN")}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => toast.info("Chức năng Edit sẽ được triển khai sau")}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteVideo(video.id, video.title)}
                            disabled={deleteVideoMutation.isPending}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
