import Link from "next/link";
import { ImageAnnotation } from "@/components/ImageAnnotation";

export default function AnnotatePage() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_#fff7ed,_#f8fafc_55%,_#e2e8f0)] px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-col gap-4 rounded-[2rem] bg-slate-950 px-6 py-7 text-white shadow-2xl sm:flex-row sm:items-end sm:justify-between">
          <div className="max-w-3xl">
            <p className="text-sm font-bold uppercase tracking-[0.3em] text-amber-300">Annotation Workspace</p>
            <h1 className="mt-3 text-3xl font-black sm:text-4xl">Review model predictions and mark image regions with precision.</h1>
            <p className="mt-3 max-w-2xl text-sm text-slate-300 sm:text-base">
              Draw bounding boxes or polygon masks, assign labels, keep multiple annotations per image, and export the final set in COCO format.
            </p>
          </div>
          <Link className="inline-flex w-fit rounded-2xl bg-white/10 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/20" href="/classify">
            Back to classify
          </Link>
        </div>

        <ImageAnnotation />
      </div>
    </main>
  );
}
