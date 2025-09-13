import React from "react";

const FeatureCard = ({ icon, title, description }) => {
  return (
    <div className="bg-white rounded-xl shadow-sm p-6 flex flex-col items-center text-center">
      <div className="w-12 h-12 flex items-center justify-center rounded-full bg-primary-50 text-primary mb-4">
        {icon}
      </div>
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-sm text-gray-500">{description}</p>
    </div>
  );
};

export default FeatureCard;
