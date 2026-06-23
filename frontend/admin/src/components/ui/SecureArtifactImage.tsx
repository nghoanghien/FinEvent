"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { adminApi } from "@/lib/admin-api";
import { ErrorBlock, LoadingBlock } from "./StateBlock";

export function SecureArtifactImage({ path, alt }: { path: string; alt: string }) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const query = useQuery({
    queryKey: ["artifact-image", path],
    queryFn: () => adminApi.reportBlob(path),
  });

  useEffect(() => {
    if (!query.data) return;
    const url = URL.createObjectURL(query.data);
    setObjectUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [query.data]);

  if (query.isLoading) return <LoadingBlock label="Đang tải biểu đồ..." />;
  if (query.error) return <ErrorBlock error={query.error} onRetry={() => query.refetch()} />;
  if (!objectUrl) return null;

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={objectUrl}
      alt={alt}
      className="max-h-[720px] w-full rounded-[28px] border border-gray-100 bg-white object-contain shadow-eatzy"
    />
  );
}
