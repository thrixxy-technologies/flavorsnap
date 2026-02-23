import { useTranslation } from "next-i18next";
import { serverSideTranslations } from "next-i18next/serverSideTranslations";
import type { GetStaticProps } from "next";
import Layout from "@/components/Layout";
import Head from "next/head";
import Link from "next/link";

export default function About() {
  const { t } = useTranslation("common");

  return (
    <Layout title="About - FlavorSnap" description="Learn about FlavorSnap - AI-powered food classification app">
      <Head>
        <title>About - FlavorSnap</title>
        <meta name="description" content="Learn about FlavorSnap - AI-powered food classification app" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <div className="min-h-screen bg-gradient-to-br from-orange-50 to-white">
        {/* Navigation Header */}
        <header className="bg-white shadow-sm border-b border-gray-100">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <Link
                href="/"
                className="text-2xl font-bold text-accent hover:text-accent/80 transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 rounded-md px-2 py-1"
                aria-label="Go to homepage"
              >
                FlavorSnap 🍛
              </Link>
              <nav className="flex space-x-4">
                <Link
                  href="/"
                  className="text-gray-600 hover:text-accent transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 rounded-md px-3 py-2 text-sm font-medium"
                >
                  Home
                </Link>
                <Link
                  href="/about"
                  className="text-accent font-medium focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 rounded-md px-3 py-2 text-sm"
                  aria-current="page"
                >
                  About
                </Link>
                <Link
                  href="/contact"
                  className="text-gray-600 hover:text-accent transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 rounded-md px-3 py-2 text-sm font-medium"
                >
                  Contact
                </Link>
              </nav>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          {/* Hero Section */}
          <section className="text-center mb-16" aria-labelledby="hero-heading">
            <h1 id="hero-heading" className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">
              About FlavorSnap
            </h1>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Discover the story behind our AI-powered food classification app and how we're making food recognition accessible to everyone.
            </p>
          </section>

          {/* Mission Section */}
          <section className="mb-16" aria-labelledby="mission-heading">
            <div className="bg-white rounded-2xl shadow-lg p-8 md:p-12">
              <h2 id="mission-heading" className="text-3xl font-bold text-gray-900 mb-6">
                Our Mission
              </h2>
              <div className="grid md:grid-cols-2 gap-8 items-center">
                <div>
                  <p className="text-lg text-gray-600 mb-4">
                    At FlavorSnap, we believe that understanding food should be as simple as taking a photo. Our mission is to democratize food recognition technology, making it accessible to everyone from home cooks to nutrition enthusiasts.
                  </p>
                  <p className="text-lg text-gray-600">
                    Using cutting-edge artificial intelligence, we've created an intuitive platform that instantly identifies food items, helping users make informed decisions about their meals, track nutrition, and explore culinary diversity.
                  </p>
                </div>
                <div className="bg-gradient-to-br from-accent/20 to-orange-100 rounded-xl p-8 text-center">
                  <div className="text-6xl mb-4">🎯</div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">Making Food Recognition Simple</h3>
                  <p className="text-gray-600">AI-powered instant identification</p>
                </div>
              </div>
            </div>
          </section>

          {/* Features Grid */}
          <section className="mb-16" aria-labelledby="features-heading">
            <h2 id="features-heading" className="text-3xl font-bold text-gray-900 mb-8 text-center">
              What Makes Us Different
            </h2>
            <div className="grid md:grid-cols-3 gap-8">
              <div className="bg-white rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow">
                <div className="text-4xl mb-4">⚡</div>
                <h3 className="text-xl font-semibold text-gray-900 mb-3">Lightning Fast</h3>
                <p className="text-gray-600">
                  Get instant food recognition results in seconds, not minutes. Our optimized AI models process images quickly and accurately.
                </p>
              </div>

              <div className="bg-white rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow">
                <div className="text-4xl mb-4">🌍</div>
                <h3 className="text-xl font-semibold text-gray-900 mb-3">Global Cuisine Support</h3>
                <p className="text-gray-600">
                  Our AI recognizes thousands of dishes from around the world, supporting diverse culinary traditions and local specialties.
                </p>
              </div>

              <div className="bg-white rounded-xl shadow-md p-6 hover:shadow-lg transition-shadow">
                <div className="text-4xl mb-4">🔒</div>
                <h3 className="text-xl font-semibold text-gray-900 mb-3">Privacy First</h3>
                <p className="text-gray-600">
                  Your images are processed securely with optional local processing. We respect your privacy and never store your photos without consent.
                </p>
              </div>
            </div>
          </section>

          {/* Technology Section */}
          <section className="mb-16" aria-labelledby="tech-heading">
            <div className="bg-gradient-to-r from-accent/10 to-orange-50 rounded-2xl p-8 md:p-12">
              <h2 id="tech-heading" className="text-3xl font-bold text-gray-900 mb-6">
                Powered by Advanced AI
              </h2>
              <div className="grid md:grid-cols-2 gap-8">
                <div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-4">Cutting-Edge Technology</h3>
                  <ul className="space-y-3 text-gray-600">
                    <li className="flex items-start">
                      <span className="text-accent mr-2">✓</span>
                      <span>Deep learning models trained on millions of food images</span>
                    </li>
                    <li className="flex items-start">
                      <span className="text-accent mr-2">✓</span>
                      <span>Real-time image processing and classification</span>
                    </li>
                    <li className="flex items-start">
                      <span className="text-accent mr-2">✓</span>
                      <span>Continuous learning and model improvements</span>
                    </li>
                    <li className="flex items-start">
                      <span className="text-accent mr-2">✓</span>
                      <span>Multi-language support for global accessibility</span>
                    </li>
                  </ul>
                </div>
                <div className="bg-white/80 rounded-xl p-6">
                  <h3 className="text-xl font-semibold text-gray-900 mb-4">Performance Metrics</h3>
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-gray-600">Accuracy</span>
                        <span className="font-semibold">95%+</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div className="bg-accent h-2 rounded-full" style={{ width: '95%' }}></div>
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-gray-600">Processing Speed</span>
                        <span className="font-semibold">&lt;2s</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div className="bg-green-500 h-2 rounded-full" style={{ width: '90%' }}></div>
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-gray-600">Food Items</span>
                        <span className="font-semibold">10,000+</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div className="bg-blue-500 h-2 rounded-full" style={{ width: '85%' }}></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Team Section */}
          <section className="mb-16" aria-labelledby="team-heading">
            <h2 id="team-heading" className="text-3xl font-bold text-gray-900 mb-8 text-center">
              Meet Our Team
            </h2>
            <div className="bg-white rounded-2xl shadow-lg p-8 md:p-12">
              <div className="grid md:grid-cols-3 gap-8 text-center">
                <div>
                  <div className="w-24 h-24 bg-gradient-to-br from-accent to-orange-400 rounded-full mx-auto mb-4 flex items-center justify-center text-white text-3xl font-bold">
                    AI
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">AI Research</h3>
                  <p className="text-gray-600">Machine learning experts training the next generation of food recognition models</p>
                </div>

                <div>
                  <div className="w-24 h-24 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full mx-auto mb-4 flex items-center justify-center text-white text-3xl font-bold">
                    UX
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">Design Team</h3>
                  <p className="text-gray-600">Creating intuitive and accessible user experiences for everyone</p>
                </div>

                <div>
                  <div className="w-24 h-24 bg-gradient-to-br from-green-500 to-teal-600 rounded-full mx-auto mb-4 flex items-center justify-center text-white text-3xl font-bold">
                    ENG
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">Engineering</h3>
                  <p className="text-gray-600">Building robust, scalable infrastructure to serve millions of users</p>
                </div>
              </div>
            </div>
          </section>

          {/* CTA Section */}
          <section className="text-center" aria-labelledby="cta-heading">
            <h2 id="cta-heading" className="text-3xl font-bold text-gray-900 mb-4">
              Ready to Try FlavorSnap?
            </h2>
            <p className="text-xl text-gray-600 mb-8">
              Join thousands of users discovering food with AI-powered recognition
            </p>
            <Link
              href="/"
              className="inline-flex items-center bg-accent text-white px-8 py-4 rounded-full text-lg font-semibold hover:bg-accent/90 transition-colors focus:outline-none focus:ring-4 focus:ring-accent/50 focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
            >
              Get Started Now
              <span className="ml-2">→</span>
            </Link>
          </section>
        </main>
      </div>
    </Layout>
  );
}

export const getStaticProps: GetStaticProps = async ({ locale }) => ({
  props: {
    ...(await serverSideTranslations(locale ?? "en", ["common"])),
  },
});
