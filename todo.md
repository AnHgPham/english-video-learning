# TODO - English Video Learning Platform

## 🎯 Mục tiêu: Xây dựng nền móng vững chắc cho nền tảng học tiếng Anh qua video

---

## 📋 Phase 1: Nền Tảng Cơ Bản (Foundation)

### Module 1: Hệ Thống Người Dùng & Authentication
- [x] 1.1 - Thiết lập database schema cho users
- [x] 1.2 - Tạo trang đăng nhập/đăng xuất cơ bản
- [x] 1.3 - Tạo trang profile người dùng
- [x] 1.4 - Phân quyền user/admin

### Module 2: Quản Lý Video (Admin)
- [x] 2.1 - Thiết lập database schema cho videos
- [x] 2.2 - Tạo trang Admin Dashboard
- [ ] 2.3 - Chức năng upload video lên S3 (đang triển khai)
- [x] 2.4 - Quản lý danh sách video (CRUD)
- [x] 2.5 - Thêm metadata cho video (title, description, level)

### Module 3: Video Player Cơ Bản
- [x] 3.1 - Tạo trang danh sách video cho user
- [ ] 3.2 - Tích hợp video player cơ bản (Video.js)
- [x] 3.3 - Hiển thị thông tin video
- [x] 3.4 - Lọc video theo level/category

---

## 🚀 Phase 2: Tính Năng Học Tập Nâng Cao (Sẽ phát triển sau)

### Module 4: Phụ Đề & Subtitle
- [ ] 4.1 - Database schema cho subtitles
- [ ] 4.2 - Upload và quản lý file phụ đề (.vtt)
- [ ] 4.3 - Hiển thị phụ đề đơn ngôn ngữ
- [ ] 4.4 - Hiển thị phụ đề song ngữ
- [ ] 4.5 - Tua theo câu (sentence-based seeking)

### Module 5: Từ Điển & Lưu Từ
- [ ] 5.1 - Database schema cho vocabulary
- [ ] 5.2 - Tích hợp API từ điển
- [ ] 5.3 - Popup tra từ khi hover
- [ ] 5.4 - Lưu từ vào kho từ vựng cá nhân
- [ ] 5.5 - Trang ôn tập từ vựng

### Module 6: AI Pipeline (Tích hợp sau)
- [ ] 6.1 - Tích hợp Speech-to-Text API
- [ ] 6.2 - AI phân đoạn ngữ nghĩa
- [ ] 6.3 - AI dịch thuật đa ngôn ngữ
- [ ] 6.4 - Giao diện hậu kiểm cho Admin

### Module 7: Tìm Kiếm & Cắt Clip (Tích hợp sau)
- [ ] 7.1 - Lập chỉ mục transcript với Elasticsearch
- [ ] 7.2 - Tìm kiếm cụm từ trong video
- [ ] 7.3 - AI mở rộng truy vấn
- [ ] 7.4 - AI cắt clip thông minh
- [ ] 7.5 - Tạo và tải clip ngắn

---

## 🐛 Bugs & Issues
_(Sẽ cập nhật khi phát hiện)_

---

## 📝 Ghi Chú
- Dự án được xây dựng theo phương pháp từng bước, từ nền móng đến nâng cao
- Mỗi module được đánh số rõ ràng để dễ theo dõi
- Ưu tiên hoàn thành Phase 1 trước khi chuyển sang Phase 2
- Code được comment chi tiết bằng tiếng Việt
