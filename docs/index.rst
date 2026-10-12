News Application
================

A Django news platform for readers, journalists, editors, and publishers.
Publishers register a publication and choose their own editors and
journalists. Journalists write articles independently or for a publisher.
Editors approve articles for their publications. Independent journalists
approve their own finished drafts. Readers subscribe to publishers or
journalists and are emailed when a followed article is approved.

The project stores data in MariaDB and exposes both HTML pages and a REST
API. Generated HTML for this documentation is in ``_build/html``. Open
``_build/html/index.html`` in a browser. You do not need to rebuild the
docs to read them.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   usage
   reference

Roles
-----

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Role
     - What they can do
   * - Reader
     - View approved articles and newsletters, and manage subscriptions.
   * - Journalist
     - Create and edit their own articles and newsletters.
   * - Editor
     - Review and approve articles for the publishers they belong to.
   * - Publisher
     - Own a publication and add or remove its editors and journalists.

Further reading
---------------

Install and run instructions, including virtualenv and Docker, are in the
repository ``README.md``. Do not commit a real ``.env`` file. Copy
``.env.example`` and fill in your own database password and secret key.
