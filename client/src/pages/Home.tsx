/**
 * ============================================
 * MODULE 3: TRANG HOME - DANH SÁCH VIDEO
 * ============================================
 * Trang chủ hiển thị danh sách video học tiếng Anh
 * Có chức năng lọc theo level và category
 */

import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { APP_LOGO, APP_TITLE, getLoginUrl } from "@/const";
import { trpc } from "@/lib/trpc";
import { BookOpen, Clock, Eye, Play, Search, User } from "lucide-react";
import { useState } from "react";
import { Link } from "wouter";

export default function Home() {
  const { user, isAuthenticated, logout } = useAuth();
  
  // State cho filters
  const [selectedLevel, setSelectedLevel] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Lấy danh sách video
  const { data: videos = [], isLoading } = trpc.video.list.useQuery({
    level: selectedLevel !== "all" ? (selectedLevel as any) : undefined,
    search: searchQuery || undefined,
    limit: 20,
  });

  // Lấy danh sách categories
  const { data: categories = [] } = trpc.video.getCategories.useQuery();

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Header/Navigation */}
      <header className="border-b bg-card sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            {/* Logo & Title */}
            <Link href="/">
              <div className="flex items-center gap-3 cursor-pointer hover:opacity-80 transition-opacity">
                {APP_LOGO && (
                  <img src={APP_LOGO} alt="Logo" className="h-10 w-10 rounded-lg" />
                )}
                <div>
                  <h1 className="text-xl font-bold text-foreground">{APP_TITLE}</h1>
                  <p className="text-xs text-muted-foreground">Học tiếng Anh qua Video</p>
                </div>
              </div>
            </Link>

            {/* User Menu */}
            <div className="flex items-center gap-3">
              {isAuthenticated ? (
                <>
                  {user?.role === "admin" && (
                    <Link href="/admin">
                      <Button variant="outline" size="sm">
                        <User className="h-4 w-4 mr-2" />
                        Admin Dashboard
                      </Button>
                    </Link>
                  )}
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">
                      Xin chào, <strong>{user?.name || "User"}</strong>
                    </span>
                    <Button variant="ghost" size="sm" onClick={() => logout()}>
                      Đăng xuất
                    </Button>
                  </div>
                </>
              ) : (
                <Button asChild>
                  <a href={getLoginUrl()}>Đăng nhập</a>
                </Button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="bg-gradient-to-br from-primary/10 via-secondary/5 to-background py-16">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-4xl md:text-5xl font-bold text-foreground mb-4">
            Học Tiếng Anh Qua Video
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-8">
            Nâng cao kỹ năng tiếng Anh của bạn thông qua các video thực tế với phụ đề song ngữ, 
            tra từ tức thì và công cụ học tập thông minh.
          </p>
          
          {/* Search Bar */}
          <div className="max-w-2xl mx-auto">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Tìm kiếm video..."
                className="pl-10 h-12 text-base"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>
        </div>
      </section>

      {/* Filters Section */}
      <section className="border-b bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex items-center gap-2">
              <BookOpen className="h-5 w-5 text-muted-foreground" />
              <span className="text-sm font-medium">Lọc theo trình độ:</span>
            </div>
            
            <Select value={selectedLevel} onValueChange={setSelectedLevel}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Tất cả trình độ" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tất cả trình độ</SelectItem>
                <SelectItem value="A1">A1 - Sơ cấp</SelectItem>
                <SelectItem value="A2">A2 - Tiền trung cấp</SelectItem>
                <SelectItem value="B1">B1 - Trung cấp</SelectItem>
                <SelectItem value="B2">B2 - Trung cấp cao</SelectItem>
                <SelectItem value="C1">C1 - Nâng cao</SelectItem>
                <SelectItem value="C2">C2 - Thành thạo</SelectItem>
              </SelectContent>
            </Select>

            {selectedLevel !== "all" && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedLevel("all")}
              >
                Xóa bộ lọc
              </Button>
            )}
          </div>
        </div>
      </section>

      {/* Videos Grid */}
      <main className="flex-1 py-12">
        <div className="container mx-auto px-4">
          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <Card key={i} className="animate-pulse">
                  <div className="aspect-video bg-muted" />
                  <CardHeader>
                    <div className="h-6 bg-muted rounded mb-2" />
                    <div className="h-4 bg-muted rounded w-2/3" />
                  </CardHeader>
                </Card>
              ))}
            </div>
          ) : videos.length === 0 ? (
            <div className="text-center py-16">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-muted mb-4">
                <Play className="h-8 w-8 text-muted-foreground" />
              </div>
              <h3 className="text-xl font-semibold mb-2">Chưa có video nào</h3>
              <p className="text-muted-foreground">
                {searchQuery || selectedLevel
                  ? "Không tìm thấy video phù hợp. Thử thay đổi bộ lọc."
                  : "Hệ thống chưa có video nào. Vui lòng quay lại sau."}
              </p>
            </div>
          ) : (
            <>
              <div className="mb-6">
                <h3 className="text-2xl font-bold text-foreground">
                  Danh Sách Video
                  <span className="text-muted-foreground font-normal text-lg ml-2">
                    ({videos.length} video)
                  </span>
                </h3>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {videos.map((video) => (
                  <Link key={video.id} href={`/watch/${video.slug}`}>
                    <Card className="group hover:shadow-lg transition-all duration-300 cursor-pointer h-full">
                      {/* Thumbnail */}
                      <div className="relative aspect-video overflow-hidden rounded-t-lg bg-muted">
                        {video.thumbnailUrl ? (
                          <img
                            src={video.thumbnailUrl}
                            alt={video.title}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-primary/20 to-secondary/20">
                            <Play className="h-16 w-16 text-primary/50" />
                          </div>
                        )}
                        
                        {/* Level Badge */}
                        <Badge className="absolute top-2 left-2 bg-primary text-primary-foreground">
                          {video.level}
                        </Badge>

                        {/* Duration */}
                        {video.duration && (
                          <Badge variant="secondary" className="absolute bottom-2 right-2">
                            <Clock className="h-3 w-3 mr-1" />
                            {Math.floor(video.duration / 60)}:{String(video.duration % 60).padStart(2, '0')}
                          </Badge>
                        )}
                      </div>

                      <CardHeader>
                        <CardTitle className="line-clamp-2 group-hover:text-primary transition-colors">
                          {video.title}
                        </CardTitle>
                        {video.description && (
                          <CardDescription className="line-clamp-2">
                            {video.description}
                          </CardDescription>
                        )}
                      </CardHeader>

                      <CardFooter className="flex items-center justify-between text-sm text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <Eye className="h-4 w-4" />
                          <span>{video.viewCount || 0} lượt xem</span>
                        </div>
                        <Badge variant="outline">{video.language === "en" ? "English" : video.language}</Badge>
                      </CardFooter>
                    </Card>
                  </Link>
                ))}
              </div>
            </>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t bg-card py-8">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          <p>© 2025 {APP_TITLE}. Nền tảng học tiếng Anh qua video.</p>
        </div>
      </footer>
    </div>
  );
}
