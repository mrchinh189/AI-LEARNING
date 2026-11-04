# Xây dựng Web App cho người mới — Tài liệu thiết kế giải pháp kỹ thuật

> **Đối tượng:** người mới (biết HTML/CSS/JavaScript cơ bản, chưa từng làm full-stack)
> **Mục tiêu:** đi từ con số 0 đến một web app thật: có đăng nhập, có database, chạy trên Internet, có test và CI
> **Ứng dụng mẫu:** **TaskNote**, quản lý công việc cá nhân/nhóm nhỏ (dự án → công việc → trạng thái)
> **Stack đề xuất:** Next.js (App Router) + TypeScript + Tailwind CSS + PostgreSQL + Prisma + Better Auth, deploy lên Vercel + Neon/Supabase
> **Cập nhật:** 11/2026. Luôn cài bản ổn định mới nhất (`@latest`) và đối chiếu với tài liệu chính thức, vì API của framework thay đổi khá nhanh.

## 1. Tóm tắt

Người mới thường bị "ngợp" vì phải chọn quá nhiều thứ cùng lúc: framework frontend, backend, database, đăng nhập, hosting. Tài liệu này **chốt sẵn một lựa chọn duy nhất cho mỗi lớp** và giải thích lý do, để bạn tập trung học khái niệm thay vì so sánh công cụ.

Giải pháp cốt lõi: **một codebase TypeScript duy nhất** (Next.js full-stack). Giao diện, logic server và truy cập database nằm chung một project, deploy bằng một lệnh `git push`. Kiến trúc chia thành 4 lớp rõ ràng (UI → Server Actions/API → Service → Database) để khi app lớn lên vẫn tách được mà không phải viết lại.

## 2. Bài toán & yêu cầu

### 2.1. Bài toán

Xây dựng một web app quản lý công việc mà người mới tự làm được trong khoảng **6–8 tuần** (mỗi tuần 8–10 giờ), đồng thời học đủ các khái niệm nền tảng của phát triển web hiện đại.

### 2.2. Yêu cầu chức năng (MVP)

| # | Chức năng | Mô tả |
|---|---|---|
| F1 | Đăng ký / đăng nhập | Email + mật khẩu; tùy chọn đăng nhập bằng GitHub/Google |
| F2 | Quản lý dự án | Tạo, sửa tên, xóa dự án; mỗi người chỉ thấy dự án của mình |
| F3 | Quản lý công việc | Thêm/sửa/xóa task trong dự án; trạng thái `TODO` → `DOING` → `DONE`; hạn chót; độ ưu tiên |
| F4 | Lọc & tìm kiếm | Lọc theo trạng thái, tìm theo tiêu đề |
| F5 | Giao diện responsive | Dùng tốt trên điện thoại và máy tính, có chế độ tối |

**Giai đoạn 2 (sau MVP):** mời thành viên vào dự án, bình luận, đính kèm file, thông báo email, kéo-thả kiểu Kanban.

### 2.3. Yêu cầu phi chức năng

| Nhóm | Yêu cầu cụ thể |
|---|---|
| Hiệu năng | Trang tải lần đầu < 2,5 giây (LCP) trên 4G; thao tác thêm task phản hồi < 300 ms |
| Bảo mật | Mật khẩu được hash; mọi truy vấn lọc theo `userId`; validate input ở server; HTTPS; không commit secret |
| Độ tin cậy | Database có backup tự động; migration có version |
| Chi phí | **0 đồng** ở giai đoạn học (dùng free tier) |
| Bảo trì | TypeScript strict, lint + format tự động, test cho logic chính, CI chạy trên mỗi Pull Request |

### 2.4. Ngoài phạm vi

App mobile native, realtime nhiều người cùng sửa, microservices, Kubernetes, thanh toán. Đây là những thứ **không nên** học trong dự án đầu tiên.

## 3. Kiến trúc tổng thể

```mermaid
flowchart TB
    subgraph Client["Trình duyệt người dùng"]
        UI["React Components<br/>(Server + Client Components)"]
    end

    subgraph Vercel["Vercel (hosting + CDN)"]
        subgraph Next["Next.js App"]
            MW["proxy / middleware<br/>chặn route chưa đăng nhập"]
            PAGES["app/ — Pages & Layouts<br/>(render phía server)"]
            ACT["Server Actions<br/>(form, mutation)"]
            API["Route Handlers app/api/*<br/>(REST cho bên ngoài)"]
            SVC["lib/services — nghiệp vụ<br/>+ kiểm tra quyền"]
            VAL["lib/validations — Zod schema"]
            AUTH["Better Auth<br/>(session, cookie)"]
            ORM["Prisma Client"]
        end
    end

    subgraph Data["Dịch vụ dữ liệu"]
        PG[("PostgreSQL<br/>Neon / Supabase")]
        MAIL["Resend<br/>(email, giai đoạn 2)"]
    end

    UI -->|HTTP request| MW
    MW --> PAGES
    UI -->|submit form| ACT
    PAGES --> SVC
    ACT --> VAL --> SVC
    API --> VAL
    API --> SVC
    SVC --> AUTH
    SVC --> ORM --> PG
    AUTH --> ORM
    SVC -.-> MAIL
```

**Giải thích các lớp:**

1. **UI (React Components):** chỉ lo hiển thị. Server Component lấy dữ liệu trực tiếp trên server (không cần gọi API); Client Component (`"use client"`) dùng khi cần tương tác như click, state, form động.
2. **Server Actions / Route Handlers:** "cửa vào" của server. Server Action dùng cho form trong chính app; Route Handler (`app/api/...`) dùng khi cần API REST cho bên thứ ba hoặc webhook.
3. **Service (`lib/services`):** nơi duy nhất chứa nghiệp vụ và kiểm tra quyền ("task này có thuộc user đang đăng nhập không?"). UI và API đều gọi qua đây, nên quy tắc chỉ viết một lần.
4. **Data (Prisma + PostgreSQL):** Prisma sinh type TypeScript từ schema, nên sai tên cột sẽ báo lỗi ngay khi viết code.

> **Nguyên tắc vàng cho người mới:** component không được gọi `prisma` trực tiếp. Luôn đi qua service. Nhờ vậy sau này muốn tách backend riêng chỉ cần chuyển thư mục `lib/services`.

## 4. Thành phần chính

### 4.1. Cấu trúc thư mục

```text
tasknote/
├── prisma/
│   ├── schema.prisma          # định nghĩa bảng
│   ├── migrations/            # lịch sử thay đổi DB (commit vào git)
│   └── seed.ts                # dữ liệu mẫu
├── src/
│   ├── app/
│   │   ├── (auth)/            # nhóm route không cần layout chính
│   │   │   ├── login/page.tsx
│   │   │   └── register/page.tsx
│   │   ├── (dashboard)/
│   │   │   ├── layout.tsx     # sidebar + header, kiểm tra session
│   │   │   ├── projects/page.tsx
│   │   │   └── projects/[projectId]/page.tsx
│   │   ├── api/
│   │   │   ├── auth/[...all]/route.ts   # endpoint của Better Auth
│   │   │   └── v1/tasks/route.ts        # REST API (tùy chọn)
│   │   ├── layout.tsx         # layout gốc: font, theme
│   │   ├── page.tsx           # landing page
│   │   └── globals.css
│   ├── components/
│   │   ├── ui/                # nút, input, dialog (shadcn/ui)
│   │   └── tasks/             # TaskList, TaskItem, TaskForm
│   ├── lib/
│   │   ├── auth.ts            # cấu hình Better Auth
│   │   ├── auth-client.ts     # hàm signIn/signOut dùng ở client
│   │   ├── db.ts              # Prisma Client singleton
│   │   ├── services/          # project.service.ts, task.service.ts
│   │   ├── validations/       # task.schema.ts (Zod)
│   │   └── actions/           # task.actions.ts ("use server")
│   └── proxy.ts               # (middleware.ts ở Next.js cũ hơn)
├── tests/
│   ├── unit/                  # Vitest
│   └── e2e/                   # Playwright
├── .env.example               # mẫu biến môi trường (KHÔNG chứa secret thật)
├── .github/workflows/ci.yml
└── package.json
```

### 4.2. Trách nhiệm từng thành phần

| Thành phần | Vị trí | Trách nhiệm | Không được làm |
|---|---|---|---|
| Page / Layout | `src/app/**/page.tsx` | Lấy dữ liệu qua service, ghép component | Chứa logic nghiệp vụ |
| Component | `src/components/**` | Hiển thị, nhận props, phát sự kiện | Gọi Prisma, đọc `process.env` bí mật |
| Server Action | `src/lib/actions/*.ts` | Nhận form → validate → gọi service → `revalidatePath` | Bỏ qua bước validate |
| Service | `src/lib/services/*.ts` | Nghiệp vụ + kiểm tra quyền sở hữu | Biết gì về HTML/React |
| Validation | `src/lib/validations/*.ts` | Zod schema dùng chung client & server | Chứa logic DB |
| Auth | `src/lib/auth.ts` | Tạo/kiểm tra session, hash mật khẩu | Tự viết thuật toán hash |
| DB client | `src/lib/db.ts` | Một instance Prisma duy nhất | Tạo `new PrismaClient()` ở nhiều nơi |

## 5. Luồng xử lý chính

### 5.1. Đăng nhập

```mermaid
sequenceDiagram
    actor U as Người dùng
    participant B as Trình duyệt
    participant N as Next.js (Better Auth)
    participant DB as PostgreSQL

    U->>B: Nhập email + mật khẩu
    B->>N: POST /api/auth/sign-in/email
    N->>DB: Tìm user theo email
    DB-->>N: user + password hash
    N->>N: So sánh mật khẩu với hash
    alt Đúng
        N->>DB: Tạo bản ghi Session
        N-->>B: Set-Cookie (HttpOnly, Secure, SameSite=Lax)
        B->>N: GET /projects (kèm cookie)
        N->>DB: Kiểm tra session
        N-->>B: HTML trang dự án
    else Sai
        N-->>B: 401 "Email hoặc mật khẩu không đúng"
    end
```

Điểm cần hiểu: session được lưu trong **cookie HttpOnly**, JavaScript ở trình duyệt không đọc được, nên an toàn hơn lưu token trong `localStorage`.

### 5.2. Thêm một công việc (Server Action)

```mermaid
sequenceDiagram
    actor U as Người dùng
    participant F as TaskForm (Client)
    participant A as createTask (Server Action)
    participant S as task.service
    participant DB as PostgreSQL

    U->>F: Gõ tiêu đề, bấm "Thêm"
    F->>F: Validate nhanh bằng Zod (UX)
    F->>A: Gọi action với FormData
    A->>A: Lấy session, validate lại bằng Zod
    A->>S: createTask(userId, input)
    S->>DB: Kiểm tra project thuộc userId
    alt Có quyền
        S->>DB: INSERT task
        DB-->>S: task mới
        S-->>A: task
        A->>A: revalidatePath("/projects/[id]")
        A-->>F: { ok: true }
        F-->>U: Danh sách cập nhật
    else Không có quyền
        S-->>A: lỗi FORBIDDEN
        A-->>F: { ok: false, error }
        F-->>U: Hiện thông báo lỗi
    end
```

> Validate **hai lần**: ở client cho trải nghiệm nhanh, ở server để bảo mật. Dữ liệu từ client luôn có thể bị giả mạo.

## 6. Mô hình dữ liệu & giao diện

### 6.1. Sơ đồ quan hệ (ERD)

```mermaid
erDiagram
    USER ||--o{ SESSION : "có"
    USER ||--o{ ACCOUNT : "liên kết"
    USER ||--o{ PROJECT : "sở hữu"
    PROJECT ||--o{ TASK : "chứa"

    USER {
        string id PK
        string email UK
        string name
        boolean emailVerified
        datetime createdAt
    }
    PROJECT {
        string id PK
        string name
        string ownerId FK
        datetime createdAt
    }
    TASK {
        string id PK
        string title
        string description
        enum status "TODO | DOING | DONE"
        enum priority "LOW | MEDIUM | HIGH"
        datetime dueDate
        string projectId FK
        datetime createdAt
        datetime updatedAt
    }
```

Bảng `User`, `Session`, `Account`, `Verification` do Better Auth sinh ra bằng lệnh `npx @better-auth/cli generate`. Bạn chỉ tự viết `Project` và `Task`.

### 6.2. Prisma schema (phần tự viết)

```prisma
// prisma/schema.prisma (trích)
enum TaskStatus {
  TODO
  DOING
  DONE
}

enum Priority {
  LOW
  MEDIUM
  HIGH
}

model Project {
  id        String   @id @default(cuid())
  name      String   @db.VarChar(100)
  ownerId   String
  owner     User     @relation(fields: [ownerId], references: [id], onDelete: Cascade)
  tasks     Task[]
  createdAt DateTime @default(now())

  @@index([ownerId])
}

model Task {
  id          String     @id @default(cuid())
  title       String     @db.VarChar(200)
  description String?
  status      TaskStatus @default(TODO)
  priority    Priority   @default(MEDIUM)
  dueDate     DateTime?
  projectId   String
  project     Project    @relation(fields: [projectId], references: [id], onDelete: Cascade)
  createdAt   DateTime   @default(now())
  updatedAt   DateTime   @updatedAt

  @@index([projectId, status])
}
```

Lưu ý thiết kế: dùng `cuid()` thay số tự tăng để người khác không đoán được ID; `onDelete: Cascade` để xóa dự án thì task bị xóa theo; index `[projectId, status]` phục vụ đúng truy vấn lọc phổ biến nhất.

### 6.3. Code mẫu từng lớp

**Prisma Client singleton** (tránh tạo quá nhiều kết nối khi dev server hot-reload):

```ts
// src/lib/db.ts (Prisma 7: cần driver adapter; bản cũ hơn bỏ phần adapter)
import { PrismaClient } from "@/generated/prisma/client";
import { PrismaPg } from "@prisma/adapter-pg";

const globalForPrisma = globalThis as unknown as { prisma?: PrismaClient };

const adapter = new PrismaPg({ connectionString: process.env.DATABASE_URL! });

export const prisma = globalForPrisma.prisma ?? new PrismaClient({ adapter });

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = prisma;
```

**Cấu hình đăng nhập:**

```ts
// src/lib/auth.ts
import { betterAuth } from "better-auth";
import { prismaAdapter } from "better-auth/adapters/prisma";
import { prisma } from "./db";

export const auth = betterAuth({
  database: prismaAdapter(prisma, { provider: "postgresql" }),
  emailAndPassword: { enabled: true, minPasswordLength: 8 },
  socialProviders: {
    github: {
      clientId: process.env.GITHUB_CLIENT_ID!,
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
    },
  },
});
```

```ts
// src/app/api/auth/[...all]/route.ts
import { auth } from "@/lib/auth";
import { toNextJsHandler } from "better-auth/next-js";

export const { GET, POST } = toNextJsHandler(auth);
```

**Validation dùng chung:**

```ts
// src/lib/validations/task.schema.ts
import { z } from "zod";

export const createTaskSchema = z.object({
  projectId: z.string().min(1),
  title: z.string().trim().min(1, "Tiêu đề không được trống").max(200),
  priority: z.enum(["LOW", "MEDIUM", "HIGH"]).default("MEDIUM"),
  dueDate: z.coerce.date().optional(),
});

export type CreateTaskInput = z.infer<typeof createTaskSchema>;
```

**Service: nghiệp vụ + kiểm tra quyền:**

```ts
// src/lib/services/task.service.ts
import { prisma } from "@/lib/db";
import type { CreateTaskInput } from "@/lib/validations/task.schema";

export class ForbiddenError extends Error {}

async function assertProjectOwner(userId: string, projectId: string) {
  const project = await prisma.project.findFirst({
    where: { id: projectId, ownerId: userId },
    select: { id: true },
  });
  if (!project) throw new ForbiddenError("Không có quyền với dự án này");
}

export async function listTasks(userId: string, projectId: string, status?: string) {
  await assertProjectOwner(userId, projectId);
  return prisma.task.findMany({
    where: { projectId, ...(status ? { status: status as never } : {}) },
    orderBy: [{ status: "asc" }, { dueDate: "asc" }],
  });
}

export async function createTask(userId: string, input: CreateTaskInput) {
  await assertProjectOwner(userId, input.projectId);
  return prisma.task.create({ data: input });
}
```

**Server Action:**

```ts
// src/lib/actions/task.actions.ts
"use server";

import { headers } from "next/headers";
import { revalidatePath } from "next/cache";
import { auth } from "@/lib/auth";
import { createTaskSchema } from "@/lib/validations/task.schema";
import { createTask, ForbiddenError } from "@/lib/services/task.service";

export type ActionResult = { ok: true } | { ok: false; error: string };

export async function createTaskAction(_prev: ActionResult | null, formData: FormData): Promise<ActionResult> {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) return { ok: false, error: "Bạn cần đăng nhập" };

  const parsed = createTaskSchema.safeParse(Object.fromEntries(formData));
  if (!parsed.success) return { ok: false, error: parsed.error.issues[0].message };

  try {
    await createTask(session.user.id, parsed.data);
  } catch (e) {
    if (e instanceof ForbiddenError) return { ok: false, error: e.message };
    throw e; // lỗi không lường trước: để Next.js hiển thị error boundary
  }

  revalidatePath(`/projects/${parsed.data.projectId}`);
  return { ok: true };
}
```

**Client Component dùng action:**

```tsx
// src/components/tasks/task-form.tsx
"use client";

import { useActionState } from "react";
import { createTaskAction } from "@/lib/actions/task.actions";

export function TaskForm({ projectId }: { projectId: string }) {
  const [state, formAction, pending] = useActionState(createTaskAction, null);

  return (
    <form action={formAction} className="flex gap-2">
      <input type="hidden" name="projectId" value={projectId} />
      <input name="title" placeholder="Việc cần làm..." required className="flex-1 rounded border px-3 py-2" />
      <button disabled={pending} className="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50">
        {pending ? "Đang thêm..." : "Thêm"}
      </button>
      {state && !state.ok && <p className="text-sm text-red-600">{state.error}</p>}
    </form>
  );
}
```

### 6.4. REST API (tùy chọn, khi cần cho app khác gọi)

| Method | Endpoint | Mô tả | Mã trả về |
|---|---|---|---|
| `GET` | `/api/v1/projects` | Danh sách dự án của tôi | 200, 401 |
| `POST` | `/api/v1/projects` | Tạo dự án | 201, 400, 401 |
| `GET` | `/api/v1/projects/:id/tasks?status=TODO` | Danh sách task | 200, 401, 403 |
| `POST` | `/api/v1/tasks` | Tạo task | 201, 400, 401, 403 |
| `PATCH` | `/api/v1/tasks/:id` | Cập nhật (trạng thái, tiêu đề...) | 200, 400, 401, 403, 404 |
| `DELETE` | `/api/v1/tasks/:id` | Xóa task | 204, 401, 403, 404 |

Định dạng lỗi thống nhất: `{ "error": { "code": "VALIDATION_ERROR", "message": "..." } }`. Route Handler gọi **cùng service** với Server Action, nên không viết trùng logic.

### 6.5. Biến môi trường

```bash
# .env.example — copy thành .env.local rồi điền giá trị thật
DATABASE_URL="postgresql://user:password@host/db?sslmode=require"
BETTER_AUTH_SECRET="chuỗi ngẫu nhiên 32+ ký tự (openssl rand -base64 32)"
BETTER_AUTH_URL="http://localhost:3000"
GITHUB_CLIENT_ID=""
GITHUB_CLIENT_SECRET=""
```

Chỉ biến có tiền tố `NEXT_PUBLIC_` mới được gửi xuống trình duyệt. **Không bao giờ** đặt secret với tiền tố này.

## 7. Tech stack

| Lớp | Công nghệ | Vai trò | Vì sao chọn cho người mới |
|---|---|---|---|
| Ngôn ngữ | **TypeScript** (strict) | Toàn bộ code | Bắt lỗi ngay khi gõ, editor gợi ý tốt |
| Runtime | **Node.js LTS** (≥ 22) | Chạy dev server, build | Chuẩn phổ biến nhất |
| Framework | **Next.js** (App Router) | Routing, render server, Server Actions, API | Một project cho cả frontend lẫn backend; tài liệu và cộng đồng lớn nhất |
| UI | **React** + **Tailwind CSS** + **shadcn/ui** | Component, style | Tailwind đỡ phải đặt tên class; shadcn/ui copy code về project nên dễ đọc, dễ sửa |
| Form & validate | **Zod** (+ React Hook Form khi form phức tạp) | Kiểm tra dữ liệu | Một schema dùng chung client/server, sinh type tự động |
| Database | **PostgreSQL** trên **Neon** hoặc **Supabase** | Lưu dữ liệu | SQL chuẩn công nghiệp, free tier đủ dùng, có branch/backup |
| ORM | **Prisma** | Truy vấn DB, migration | Schema dễ đọc, type-safe, có Prisma Studio để xem dữ liệu |
| Auth | **Better Auth** | Đăng ký, đăng nhập, session, OAuth | Tự host, dữ liệu user nằm trong DB của bạn; dự án Auth.js hiện cũng do nhóm Better Auth duy trì |
| Test | **Vitest** + **Testing Library**, **Playwright** | Unit test, E2E test | Nhanh, cú pháp giống Jest |
| Chất lượng code | **ESLint** + **Prettier** | Lint, format | Tự sửa phần lớn lỗi vặt |
| CI | **GitHub Actions** | Chạy lint/test/build mỗi PR | Miễn phí cho repo public |
| Hosting | **Vercel** | Deploy, preview mỗi PR, HTTPS | Do chính nhóm Next.js làm, cấu hình gần như bằng 0 |
| Giám sát | **Sentry** (lỗi), **Vercel Analytics** | Theo dõi lỗi, hiệu năng | Có free tier |
| Email (GĐ 2) | **Resend** + React Email | Email xác thực, thông báo | API đơn giản |

### 7.1. Phương án thay thế (khi nào nên chọn)

| Tình huống | Thay bằng |
|---|---|
| Chưa muốn học SQL/ORM, muốn có sẵn auth + storage + realtime | **Supabase** trọn gói (Auth + Postgres + Storage), bỏ Prisma và Better Auth |
| Đã quen Python | **FastAPI** + SQLAlchemy + PostgreSQL ở backend, **React + Vite** ở frontend (2 project tách riêng) |
| Chỉ cần trang tĩnh/blog | **Astro** hoặc Next.js static export, không cần database |
| Muốn SQL "sát kim loại" hơn Prisma | **Drizzle ORM** |
| Không muốn phụ thuộc Vercel | Docker + **Railway / Render / Fly.io**, hoặc VPS + Coolify |

## 8. Quyết định thiết kế & đánh đổi

| Quyết định | Lý do | Đánh đổi |
|---|---|---|
| Monolith full-stack (Next.js) thay vì frontend + backend tách riêng | Một repo, một lần deploy, chia sẻ type giữa client và server | Khi cần backend cho mobile app phải thêm Route Handler hoặc tách ra sau |
| Server Components + Server Actions thay vì gọi API bằng `fetch` từ client | Ít code hơn, không phải tự quản lý loading/cache cho dữ liệu đọc | Phải hiểu ranh giới server/client; khó debug hơn lúc đầu |
| PostgreSQL thay vì MongoDB | Dữ liệu có quan hệ rõ ràng (user → project → task); SQL là kỹ năng bền vững | Phải viết migration khi đổi schema |
| Prisma thay vì SQL thuần | Type-safe, migration tự động, dễ học | Thêm một lớp trừu tượng; truy vấn phức tạp có thể cần `$queryRaw` |
| Tự host auth (Better Auth) thay vì dịch vụ (Clerk, Auth0) | Không bị khóa vào nhà cung cấp, học được cơ chế session/cookie | Tự chịu trách nhiệm cấu hình đúng (secret, HTTPS, rate limit) |
| Lớp service tách riêng | Kiểm tra quyền ở một chỗ, dễ test, dễ tách backend sau này | Thêm một tầng file so với gọi Prisma trực tiếp trong page |
| Kiểm tra quyền bằng `where: { ownerId: userId }` ở mọi truy vấn | Chặn lỗi IDOR (đoán ID để xem dữ liệu người khác), lỗi phổ biến nhất của app mới | Phải nhớ áp dụng nhất quán, nên viết test cho nó |
| Deploy Vercel + Neon | Free, preview URL cho mỗi PR, không cần biết DevOps | Giới hạn free tier; serverless có cold start; DB ngủ khi không dùng |

## 9. Triển khai & vận hành

### 9.1. Khởi tạo dự án (làm một lần)

```bash
npx create-next-app@latest tasknote --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
```

```bash
cd tasknote && npm install prisma @prisma/client @prisma/adapter-pg better-auth zod
```

```bash
npm install -D vitest @testing-library/react @playwright/test prettier
```

```bash
npx prisma init
```

```bash
npx shadcn@latest init
```

### 9.2. Chu trình làm việc hằng ngày

```mermaid
flowchart LR
    A["Tạo nhánh<br/>git checkout -b feat/xxx"] --> B["Code + chạy<br/>npm run dev"]
    B --> C{"Đổi schema DB?"}
    C -->|Có| D["npx prisma migrate dev<br/>--name ten_thay_doi"]
    C -->|Không| E["Viết/chạy test<br/>npm test"]
    D --> E
    E --> F["git commit + push"]
    F --> G["Mở Pull Request"]
    G --> H["CI: lint, typecheck,<br/>test, build"]
    H --> I["Vercel Preview URL<br/>kiểm tra thực tế"]
    I --> J["Merge vào main"]
    J --> K["Vercel deploy production<br/>+ prisma migrate deploy"]
```

### 9.3. CI với GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI
on:
  pull_request:
  push:
    branches: [main]

jobs:
  check:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: tasknote_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready --health-interval 5s --health-timeout 5s --health-retries 10
    env:
      DATABASE_URL: postgresql://postgres:postgres@localhost:5432/tasknote_test
      BETTER_AUTH_SECRET: ci-only-secret-not-for-production
      BETTER_AUTH_URL: http://localhost:3000
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
      - run: npm ci
      - run: npx prisma migrate deploy
      - run: npm run lint
      - run: npx tsc --noEmit
      - run: npm test -- --run
      - run: npm run build
```

### 9.4. Deploy production

1. Tạo database trên **Neon** (hoặc Supabase), lấy `DATABASE_URL` có `sslmode=require`.
2. Import repo GitHub vào **Vercel**, khai báo biến môi trường ở mục *Settings → Environment Variables* (tách riêng Production và Preview, Preview nên trỏ tới một DB branch khác).
3. Đặt build command: `prisma generate && prisma migrate deploy && next build` (hoặc chạy migrate trong một bước CI riêng trước khi deploy).
4. Cấu hình OAuth GitHub với callback URL `https://<domain>/api/auth/callback/github`.
5. Bật **Sentry** để nhận báo lỗi và **Vercel Analytics** để xem Core Web Vitals.

### 9.5. Checklist bảo mật trước khi công khai

- [ ] `.env*` nằm trong `.gitignore`; đã quét lịch sử git để chắc không lộ secret
- [ ] Mọi Server Action và Route Handler đều kiểm tra session trước tiên
- [ ] Mọi truy vấn dữ liệu của user đều lọc theo `userId`/`ownerId` (có test chứng minh user A không đọc được task của user B)
- [ ] Mọi input đều qua Zod ở server
- [ ] Không render HTML từ người dùng bằng `dangerouslySetInnerHTML` (nếu bắt buộc thì sanitize)
- [ ] Bật rate limit cho endpoint đăng nhập/đăng ký (Better Auth có sẵn tùy chọn `rateLimit`)
- [ ] Thông báo lỗi không lộ stack trace hay câu SQL
- [ ] `npm audit` không còn lỗ hổng mức high/critical
- [ ] Bật backup tự động (point-in-time restore) cho database

### 9.6. Giới hạn đã biết

- Free tier của Neon/Supabase có thể "ngủ" DB khi không dùng, nên request đầu tiên chậm vài giây.
- Serverless function có giới hạn thời gian chạy; tác vụ nặng (xuất báo cáo lớn, gửi email hàng loạt) cần hàng đợi riêng như Inngest, Trigger.dev hoặc QStash.
- Server Actions phù hợp cho mutation trong app, không thay được API công khai có version.

## 10. Điểm mở rộng

| Nhu cầu | Cách mở rộng | Chỗ cần sửa |
|---|---|---|
| Nhiều thành viên trong dự án | Thêm bảng `ProjectMember(projectId, userId, role)`; đổi `assertProjectOwner` thành `assertProjectRole` | `schema.prisma`, `lib/services` |
| Upload file đính kèm | Lưu file lên Vercel Blob / Supabase Storage / S3, DB chỉ lưu URL | Thêm `lib/storage.ts`, bảng `Attachment` |
| Thông báo email | Resend + React Email; gửi qua hàng đợi nếu nhiều | `lib/mail.ts` |
| Kéo-thả Kanban | `dnd-kit` ở client, thêm cột `position` cho Task | `components/tasks`, schema |
| Realtime | Supabase Realtime, Pusher/Ably hoặc polling 10–30 giây (đơn giản nhất) | Client Component |
| Đa ngôn ngữ | `next-intl` | `app/[locale]/...` |
| Tính năng AI (tóm tắt task, gợi ý chia nhỏ việc) | Gọi API LLM (vd. Claude) từ Server Action, stream kết quả bằng Vercel AI SDK | `lib/ai.ts`, không bao giờ gọi từ client với API key |
| App mobile | Dùng lại `app/api/v1/*` + service; xác thực bằng bearer token | Route Handlers |

## 11. Lộ trình học & triển khai (8 tuần)

| Tuần | Mục tiêu | Kết quả bàn giao | Khái niệm cần nắm |
|---|---|---|---|
| 0 | Chuẩn bị | Cài Node LTS, VS Code, Git; tài khoản GitHub, Vercel, Neon | Terminal, git cơ bản (`clone`, `commit`, `push`, branch) |
| 1 | Nền tảng | Landing page + layout responsive deploy lên Vercel | JSX, component, props, Tailwind, routing theo thư mục |
| 2 | Giao diện tĩnh | Trang danh sách dự án/task với dữ liệu giả | State, sự kiện, list & key, Server vs Client Component |
| 3 | Database | Prisma schema, migration, seed; trang đọc dữ liệu thật | SQL cơ bản, quan hệ 1-n, migration, ORM |
| 4 | Ghi dữ liệu | Thêm/sửa/xóa task bằng Server Actions + Zod | Form, validation, `revalidatePath`, xử lý lỗi |
| 5 | Đăng nhập | Better Auth, bảo vệ route, dữ liệu theo từng user | Cookie, session, hash mật khẩu, phân quyền, IDOR |
| 6 | Chất lượng | Unit test service, 1–2 E2E test, CI xanh | Test pyramid, mock, GitHub Actions |
| 7 | Hoàn thiện | Lọc/tìm kiếm, loading/empty/error state, dark mode, accessibility | `loading.tsx`, `error.tsx`, Suspense, a11y |
| 8 | Ra mắt | Domain riêng, Sentry, checklist bảo mật, README | Biến môi trường, giám sát, backup |

### 11.1. Lỗi thường gặp của người mới

| Lỗi | Hậu quả | Cách tránh |
|---|---|---|
| Gọi DB hoặc dùng secret trong Client Component | Lộ secret, build lỗi | Chỉ truy cập DB trong service; kiểm tra file có `"use client"` hay không |
| Chỉ kiểm tra quyền ở UI (ẩn nút) | Người khác gọi thẳng action vẫn sửa được dữ liệu | Kiểm tra quyền ở service |
| Sửa DB bằng tay trên production | Lệch schema giữa các môi trường | Mọi thay đổi đi qua `prisma migrate` |
| Commit file `.env` | Lộ mật khẩu DB | `.gitignore` + đổi secret ngay nếu lỡ lộ |
| Thêm `"use client"` ở mọi file | Mất lợi ích render server, bundle nặng | Chỉ đánh dấu component lá cần tương tác |
| Học quá nhiều công cụ cùng lúc (Redux, GraphQL, Docker, K8s...) | Bỏ cuộc giữa chừng | Bám đúng stack trong tài liệu cho tới khi ra mắt MVP |
| Không có trạng thái loading/lỗi | Người dùng bấm nhiều lần, tạo dữ liệu trùng | `pending` từ `useActionState`, disable nút |

### 11.2. Dùng AI coding agent hiệu quả khi học

1. **Bắt AI giải thích trước khi viết code.** Ví dụ: "Giải thích Server Action khác Route Handler thế nào, rồi mới viết code".
2. **Giao việc nhỏ, có ranh giới rõ:** "Viết `task.service.ts` theo cấu trúc trong tài liệu này, kèm test Vitest", thay vì "làm cho tôi app quản lý công việc".
3. **Tự đọc từng dòng code được sinh ra** và chạy test trước khi commit. Không hiểu thì hỏi lại.
4. **Đặt quy ước vào file `CLAUDE.md`/`AGENTS.md`** trong repo (stack, cấu trúc thư mục, quy tắc "component không gọi Prisma") để agent tuân thủ nhất quán.
5. **Cẩn thận với kiến thức cũ:** framework đổi nhanh, nên yêu cầu agent kiểm tra tài liệu phiên bản hiện tại (ví dụ `middleware.ts` đã đổi tên thành `proxy.ts` ở Next.js 16).

## 12. Tham khảo

- Next.js — [Learn Next.js](https://nextjs.org/learn) và [Docs](https://nextjs.org/docs)
- React — [react.dev/learn](https://react.dev/learn)
- TypeScript — [Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
- Tailwind CSS — [tailwindcss.com/docs](https://tailwindcss.com/docs) · shadcn/ui — [ui.shadcn.com](https://ui.shadcn.com)
- Prisma — [prisma.io/docs](https://www.prisma.io/docs) (đọc kỹ hướng dẫn nâng cấp nếu dùng Prisma 7)
- Better Auth — [better-auth.com/docs](https://www.better-auth.com/docs)
- Zod — [zod.dev](https://zod.dev)
- Neon — [neon.com/docs](https://neon.com/docs) · Supabase — [supabase.com/docs](https://supabase.com/docs)
- Vercel — [vercel.com/docs](https://vercel.com/docs)
- Vitest — [vitest.dev](https://vitest.dev) · Playwright — [playwright.dev](https://playwright.dev)
- OWASP Top 10 — [owasp.org/Top10](https://owasp.org/Top10/) (đọc ít nhất mục Broken Access Control và Injection)
- MDN Web Docs — [developer.mozilla.org](https://developer.mozilla.org) (HTML/CSS/JS/HTTP nền tảng)
