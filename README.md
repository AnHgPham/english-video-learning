# 🎓 English Video Learning Platform

Nền tảng học tiếng Anh thông qua video với phụ đề song ngữ, tra từ tức thì và các công cụ học tập thông minh.

## ✨ Tính Năng Hiện Tại (Phase 1 - Foundation)

### 🔐 Module 1: Hệ Thống Người Dùng & Authentication
- ✅ Đăng nhập/Đăng xuất với Manus OAuth
- ✅ Phân quyền User/Admin
- ✅ Quản lý profile người dùng

### 🎬 Module 2: Quản Lý Video (Admin)
- ✅ Admin Dashboard với thống kê
- ✅ Quản lý video (CRUD operations)
- ✅ Form upload video (UI hoàn chỉnh)
- ✅ Database schema cho videos, subtitles, categories

### 📺 Module 3: Video Player Cơ Bản
- ✅ Trang danh sách video với thumbnail
- ✅ Bộ lọc theo trình độ (A1-C2)
- ✅ Tìm kiếm video
- ✅ Responsive design

## 🚀 Tính Năng Sắp Triển Khai (Phase 2)

### Module 4: Phụ Đề & Subtitle
- [ ] Upload và quản lý file phụ đề (.vtt)
- [ ] Hiển thị phụ đề song ngữ
- [ ] Tua theo câu (sentence-based seeking)

### Module 5: Từ Điển & Lưu Từ
- [ ] Tích hợp API từ điển
- [ ] Popup tra từ khi hover
- [ ] Lưu từ vào kho từ vựng cá nhân
- [ ] Trang ôn tập từ vựng

### Module 6: AI Pipeline
- [ ] Tích hợp Speech-to-Text API
- [ ] AI phân đoạn ngữ nghĩa
- [ ] AI dịch thuật đa ngôn ngữ

### Module 7: Tìm Kiếm & Cắt Clip
- [ ] Lập chỉ mục transcript với Elasticsearch
- [ ] Tìm kiếm cụm từ trong video
- [ ] AI cắt clip thông minh

## 🛠️ Tech Stack

### Backend
- **Framework**: Express.js + tRPC 11
- **Database**: MySQL/TiDB với Drizzle ORM
- **Authentication**: Manus OAuth
- **File Storage**: AWS S3

### Frontend
- **Framework**: React 19 + Vite
- **Styling**: Tailwind CSS 4
- **UI Components**: shadcn/ui
- **State Management**: TanStack Query (React Query)
- **Routing**: Wouter

### DevOps
- **Package Manager**: pnpm
- **Type Safety**: TypeScript
- **Database Migrations**: Drizzle Kit

## 📁 Cấu Trúc Dự Án

```
english_video_learning/
├── client/                 # Frontend React
│   ├── src/
│   │   ├── pages/         # Các trang (Home, AdminDashboard)
│   │   ├── components/    # UI components
│   │   ├── lib/           # tRPC client
│   │   └── App.tsx        # Routes
│   └── public/            # Static assets
├── server/                # Backend Express + tRPC
│   ├── routers.ts         # tRPC routers (đánh số module)
│   ├── db.ts              # Database helpers (đánh số module)
│   └── _core/             # Framework core
├── drizzle/               # Database schema & migrations
│   └── schema.ts          # Tables với comment chi tiết
├── shared/                # Shared types & constants
└── todo.md                # Theo dõi tiến độ
```

## 🚀 Cài Đặt và Chạy Dự Án

### Yêu Cầu
- Node.js 22.x
- pnpm
- MySQL/TiDB database

### Bước 1: Clone Repository
```bash
git clone <repository-url>
cd english_video_learning
```

### Bước 2: Cài Đặt Dependencies
```bash
pnpm install
```

### Bước 3: Cấu Hình Environment Variables
Dự án sử dụng các biến môi trường được inject tự động từ Manus platform:
- `DATABASE_URL` - MySQL connection string
- `JWT_SECRET` - Session cookie signing secret
- `OAUTH_SERVER_URL` - Manus OAuth backend
- `VITE_APP_TITLE` - Tên ứng dụng
- Và nhiều biến khác...

### Bước 4: Push Database Schema
```bash
pnpm db:push
```

### Bước 5: Chạy Development Server
```bash
pnpm dev
```

Server sẽ chạy tại `http://localhost:3000`

## 📝 Scripts Hữu Ích

```bash
# Development
pnpm dev              # Chạy dev server

# Database
pnpm db:push          # Push schema changes to database
pnpm db:studio        # Mở Drizzle Studio (database GUI)

# Build
pnpm build            # Build production
pnpm start            # Chạy production server
```

## 🎨 Design Guidelines

### Màu Sắc
- **Primary**: Xanh dương (#3B82F6) - Màu chủ đạo cho giáo dục
- **Secondary**: Xanh lá (#10B981) - Màu phụ cho accent
- **Background**: Xanh dương nhạt (#F8FAFC)

### Typography
- Font chính: System font stack (Inter, SF Pro)
- Heading: Bold, rõ ràng
- Body: Regular, dễ đọc

## 🔒 Phân Quyền

### User (Người dùng thường)
- Xem danh sách video đã publish
- Xem chi tiết video
- Tìm kiếm và lọc video
- Lưu từ vựng (sắp triển khai)

### Admin
- Tất cả quyền của User
- Truy cập Admin Dashboard
- Quản lý video (CRUD)
- Upload video và phụ đề
- Xem thống kê

## 📚 Tài Liệu Kỹ Thuật

### Database Schema
Xem file `drizzle/schema.ts` với comment chi tiết về:
- Bảng `users` - Thông tin người dùng
- Bảng `videos` - Thông tin video
- Bảng `subtitles` - Phụ đề đa ngôn ngữ
- Bảng `categories` - Danh mục video
- Bảng `user_vocabulary` - Từ vựng đã lưu

### API Routes (tRPC)
Xem file `server/routers.ts` với các router:
- `auth.*` - Authentication
- `video.*` - Video management (public)
- `admin.*` - Admin operations

### Database Helpers
Xem file `server/db.ts` với các helper functions được đánh số module rõ ràng.

## 🤝 Đóng Góp

Dự án đang trong giai đoạn phát triển. Mọi đóng góp đều được chào đón!

### Quy Trình Đóng Góp
1. Fork repository
2. Tạo branch mới (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Mở Pull Request

### Code Style
- Sử dụng TypeScript strict mode
- Comment bằng tiếng Việt cho dễ hiểu
- Đánh số module rõ ràng (Module 1, Module 2, ...)
- Follow existing patterns trong codebase

## 📋 Roadmap

### Q1 2025
- ✅ Hoàn thành Phase 1: Foundation
- 🔄 Triển khai Video Player với Video.js
- 🔄 Tích hợp upload S3

### Q2 2025
- [ ] Phụ đề song ngữ
- [ ] Tra từ tức thì
- [ ] Lưu từ vựng

### Q3 2025
- [ ] AI Pipeline (STT, Translation)
- [ ] Tìm kiếm & cắt clip thông minh

## 📄 License

MIT License - Xem file LICENSE để biết thêm chi tiết

## 👥 Tác Giả

Dự án được xây dựng với ❤️ bởi Manus AI

## 🙏 Acknowledgments

- [shadcn/ui](https://ui.shadcn.com/) - UI Components
- [tRPC](https://trpc.io/) - End-to-end typesafe APIs
- [Drizzle ORM](https://orm.drizzle.team/) - TypeScript ORM
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS

---

**⭐ Nếu bạn thấy dự án hữu ích, hãy cho một star nhé!**
