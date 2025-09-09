import React from "react";
import Button from "../../System Design/Button";
import FeatureCard from "../../System Design/FeatureCard";
import DocumentItem from "../../System Design/DocumentItem";
import { Search, FileText, BookOpen } from "lucide-react";

const Home = () => {
  return (
    <div className="flex-1 p-8 overflow-y-auto">
      {/* Hero */}
      <div className="bg-blue-50 rounded-xl p-10 text-center">
        <h1 className="text-3xl font-bold mb-4">
          Lisez vos PDF <span className="text-blue-600">intelligemment</span>
        </h1>
        <p className="text-gray-600 mb-6">
          Transformez vos documents PDF en expérience de lecture interactive avec sommaire automatique et navigation fluide.
        </p>
        <div className="flex justify-center gap-4">
          <Button variant="primary">Télécharger un PDF</Button>
          <Button variant="secondary">Voir ma bibliothèque</Button>
        </div>
      </div>

      {/* Features */}
      <h2 className="text-xl font-bold mt-12 mb-6 text-center">
        Une expérience de lecture révolutionnaire
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <FeatureCard icon={<Search size={24} />} title="Analyse Automatique" description="Notre IA extrait automatiquement le sommaire et structure le contenu." />
        <FeatureCard icon={<BookOpen size={24} />} title="Navigation Intelligente" description="Naviguez facilement grâce au sommaire interactif et liens rapides." />
        <FeatureCard icon={<FileText size={24} />} title="Interface Moderne" description="Design épuré et ergonomique, optimisé pour tous vos appareils." />
      </div>

      {/* Documents récents */}
      <div className="mt-12">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">Documents Récents</h2>
          <button className="text-blue-600 hover:text-blue-800 text-sm">Voir tout →</button>
        </div>
        <input
          type="text"
          placeholder="Rechercher dans vos documents..."
          className="w-full mb-6 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-none"
        />
        <div className="flex flex-col gap-4">
          <DocumentItem title="NDC Orange Perpignan V4" date="08/09/2025" sections={259} />
          <DocumentItem title="Guide du Développeur React" date="08/09/2025" sections={5} />
        </div>
      </div>
    </div>
  );
};

export default Home;
