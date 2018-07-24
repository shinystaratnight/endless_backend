from dry_rest_permissions.generics import DRYPermissions


class CandidateContactPermissions(DRYPermissions):
    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated or not user.contact:
            return False

        company = user.contact.get_closest_company()
        return obj.candidate_rels.filter(master_company=company, active=True).exists()
