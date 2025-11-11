CREATE TABLE `categories` (
	`id` int AUTO_INCREMENT NOT NULL,
	`name` varchar(100) NOT NULL,
	`slug` varchar(100) NOT NULL,
	`description` text,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `categories_id` PRIMARY KEY(`id`),
	CONSTRAINT `categories_slug_unique` UNIQUE(`slug`)
);
--> statement-breakpoint
CREATE TABLE `subtitles` (
	`id` int AUTO_INCREMENT NOT NULL,
	`videoId` int NOT NULL,
	`language` varchar(10) NOT NULL,
	`languageName` varchar(50) NOT NULL,
	`subtitleUrl` text NOT NULL,
	`subtitleKey` varchar(500) NOT NULL,
	`isDefault` int NOT NULL DEFAULT 0,
	`source` enum('manual','ai_generated','imported') NOT NULL DEFAULT 'manual',
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `subtitles_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `user_vocabulary` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`word` varchar(200) NOT NULL,
	`translation` text,
	`phonetic` varchar(100),
	`definition` text,
	`example` text,
	`videoId` int,
	`timestamp` int,
	`context` text,
	`masteryLevel` int NOT NULL DEFAULT 0,
	`reviewCount` int NOT NULL DEFAULT 0,
	`lastReviewedAt` timestamp,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `user_vocabulary_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `videos` (
	`id` int AUTO_INCREMENT NOT NULL,
	`title` varchar(255) NOT NULL,
	`slug` varchar(255) NOT NULL,
	`description` text,
	`videoUrl` text NOT NULL,
	`videoKey` varchar(500) NOT NULL,
	`thumbnailUrl` text,
	`duration` int,
	`level` enum('A1','A2','B1','B2','C1','C2') NOT NULL,
	`language` varchar(10) NOT NULL DEFAULT 'en',
	`categoryId` int,
	`uploadedBy` int NOT NULL,
	`status` enum('draft','processing','published','archived') NOT NULL DEFAULT 'draft',
	`viewCount` int NOT NULL DEFAULT 0,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	`publishedAt` timestamp,
	CONSTRAINT `videos_id` PRIMARY KEY(`id`),
	CONSTRAINT `videos_slug_unique` UNIQUE(`slug`)
);
--> statement-breakpoint
ALTER TABLE `subtitles` ADD CONSTRAINT `subtitles_videoId_videos_id_fk` FOREIGN KEY (`videoId`) REFERENCES `videos`(`id`) ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE `user_vocabulary` ADD CONSTRAINT `user_vocabulary_userId_users_id_fk` FOREIGN KEY (`userId`) REFERENCES `users`(`id`) ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE `user_vocabulary` ADD CONSTRAINT `user_vocabulary_videoId_videos_id_fk` FOREIGN KEY (`videoId`) REFERENCES `videos`(`id`) ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE `videos` ADD CONSTRAINT `videos_categoryId_categories_id_fk` FOREIGN KEY (`categoryId`) REFERENCES `categories`(`id`) ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE `videos` ADD CONSTRAINT `videos_uploadedBy_users_id_fk` FOREIGN KEY (`uploadedBy`) REFERENCES `users`(`id`) ON DELETE no action ON UPDATE no action;