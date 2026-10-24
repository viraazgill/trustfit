"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

/** Phase 5 replaces this with the readiness radar and gap cards. */
export default function Readiness() {
  const { id } = useParams<{ id: string }>();
  return (
    <p className="text-sm text-ink-muted">
      The readiness check arrives with the Gap Bridge. Meanwhile, see your{" "}
      <Link href={`/sme/${id}/matches`} className="text-blue hover:underline">
        matched partners
      </Link>
      .
    </p>
  );
}
