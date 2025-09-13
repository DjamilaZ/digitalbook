import React from "react";
import clsx from "clsx";

const NavItem = ({ icon, label, active = false }) => {
  return (
    <button
      className={clsx(
        "flex items-center gap-3 px-6 py-3 text-sm font-medium w-full text-left transition-colors",
        active
          ? "bg-primary-50 text-primary"
          : "text-gray-600 hover:bg-gray-100 hover:text-gray-800"
      )}
    >
      {icon}
      {label}
    </button>
  );
};

export default NavItem;
