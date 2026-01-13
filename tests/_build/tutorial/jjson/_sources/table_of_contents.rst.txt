.. _table-of-contents:

Table of Contents
=============================

The `toctree` directive is a powerful feature in reStructuredText (reST) used to automatically generate a Table of Contents (TOC) in Sphinx-based documentation.

The TOC serves to organize your documentation in a hierarchical structure and creates navigation links to different sections and subsections. This greatly improves readability and usability, making it easier for users to navigate the content.

Basic Usage
-----------------------------

For instance, if you have the following directory structure for your documentation:

.. code-block:: text

    docs/
    ├── index.rst
    ├── introduction.rst
    ├── installation.rst
    ├── usage.rst
    ├── chapters/
    │   ├── chapter1.rst
    │   ├── chapter2.rst
    │   ├── chapter3.rst

To add a `toctree` to an `.rst` file, you can follow this basic format:

.. code-block:: restructuredtext

    .. toctree::
        :maxdepth: 2
        :caption: Contents
        :glob:

        introduction
        installation
        usage
        chapters/*

Explanation of the Fields:

- **.. toctree::**  
  This is the directive that marks the start of the Table of Contents. It tells Sphinx to include the sections listed under it in the TOC.

- **:maxdepth:**  
  The `:maxdepth:` option controls the depth of the TOC, which refers to how many levels of sections and subsections to include. 
  - For example, `:maxdepth: 1` will only include the top-level sections.
  - Setting `:maxdepth: 2` will include the second-level sections (subsections) as well. 
  - This helps to control how much of the document hierarchy is displayed in the TOC.

- **:caption:**  
  The `:caption:` option sets the title of the TOC. In the example, `:caption: Contents` will give the TOC the title "Contents". You can change this to any title you prefer.

- **:glob:**  
  The `:glob:` option enables the use of wildcard patterns (like `*`) to match multiple files. 
  - For instance, `chapters/*` matches all `.rst` files within the `chapters` directory, including `chapter1.rst`, `chapter2.rst`, and `chapter3.rst`.

- **Listed Files/Sections:**  
  After the `toctree` directive, the filenames (without the `.rst` extension) are listed. These files will be included in the TOC and linked to the corresponding sections in your documentation.
  - Example: `introduction`, `installation`, `usage`, and `chapters/*` will be added to the TOC.
  - Files in subdirectories can be included by specifying the relative path.