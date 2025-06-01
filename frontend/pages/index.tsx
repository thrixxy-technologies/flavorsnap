import { useRouter } from "next/router";
import Image from "next/image";
import hero from "@/public/images/hero_img.png";
export default function Home() {
  const router = useRouter();

  return (
    <div className="bg-muted min-h-screen flex flex-col items-center justify-center px-4 py-8">
      <header className="text-center max-w-2xl">
        <h1 className="text-4xl md:text-5xl font-bold text-primary mb-4">
          🍲 Flavorsnap
        </h1>
        <p className="text-gray-700 text-lg mb-6">
          Snap a picture of your food and let AI identify the dish and show you
          its recipe.
        </p>
        <button
          onClick={() => router.push("/classify")}
          className="bg-accent text-white px-6 py-3 rounded-full font-semibold hover:bg-orange-600 transition"
        >
          Get Started
        </button>
      </header>

      <div className="mt-10 w-full max-w-md">
        <Image
          src={hero}
          alt="Nigerian dish"
          width={500}
          height={300}
          className="rounded-xl shadow-lg"
        />
      </div>

      <footer className="mt-12 text-gray-500 text-sm">
        Built with 💚 for Nigerian food lovers
      </footer>
    </div>
  );
}
